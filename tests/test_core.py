"""Specs 00 and 01: config, storage, error handling, shared parameter rules, sources."""
import asyncio
import json
import sqlite3
from datetime import date, datetime
from types import SimpleNamespace

import httpx
import pytest

from f1buddy import bot, config, ctx, util
from f1buddy.data import params
from f1buddy.db import Database
from f1buddy.errors import SourceError, UserError
from f1buddy.render import embeds
from f1buddy.sources import fastf1_src, http, jolpica, weather, wikipedia

from conftest import FIXTURES, UTC, FakeInteraction, fixture_json, three_race_season


# ------------------------------------------------------------------ config

def test_config_names_missing_variable():
    with pytest.raises(SystemExit, match="DISCORD_TOKEN"):
        config.load({"ADMIN_USER_IDS": "1"})


def test_config_parses_admins_and_defaults():
    cfg = config.load({"DISCORD_TOKEN": "t", "ADMIN_USER_IDS": "1, 2"})
    assert cfg.admin_ids == {1, 2} and cfg.gemini_key is None and cfg.fia_channel_id is None


# ---------------------------------------------------------------- database

def test_schema_is_versioned_and_reopens(tmp_path):
    path = tmp_path / "x.db"
    Database(path).close()
    db = Database(path)  # second open must not re-run migrations
    assert db.execute("PRAGMA user_version")[0][0] == 1
    db.close()


async def test_cache_expiry():
    await ctx.db.cache_set("a", {"v": 1}, ttl=100)
    await ctx.db.cache_set("b", 2, ttl=-1)
    assert await ctx.db.cache_get("a") == {"v": 1}
    assert await ctx.db.cache_get("b") is None
    assert await ctx.db.cache_get("missing") is None


def test_podium_columns_all_or_nothing():
    with pytest.raises(sqlite3.IntegrityError):
        ctx.db.execute("INSERT INTO predictions (guild_id,user_id,year,round,p1,updated_at) VALUES (1,1,2026,1,'VER',0)")


# ---------------------------------------------------------- error handling

def test_error_messages_never_leak_details():
    assert bot.error_message(UserError("Pick a year.")) == "Pick a year."
    assert bot.error_message(SourceError("Jolpica", "HTTP 500 secret-url")) == \
        "Couldn't reach Jolpica. Try again in a few minutes."
    assert bot.error_message(ValueError("boom")) == "Something went wrong. It's been logged."
    assert bot.error_message(SimpleNamespace(original=UserError("wrapped"))) == "wrapped"


async def test_error_reply_is_ephemeral_before_and_after_defer():
    fresh = FakeInteraction()
    await bot.on_app_command_error(fresh, UserError("nope"))
    assert fresh.response.sent[0]["ephemeral"] and fresh.response.sent[0]["embed"].description == "nope"
    deferred = FakeInteraction()
    await deferred.response.defer()
    await bot.on_app_command_error(deferred, UserError("nope"))
    assert deferred.followup.sent[0]["ephemeral"]


def test_embed_limits():
    embed = embeds.make("t" * 300, "d" * 5000)
    assert len(embed.title) == 256 and len(embed.description) == 4096
    embeds.columns(embed, ("Col", ["x" * 100] * 20))
    assert len(embed.fields[0].value) <= 1024
    assert embed.fields[0].value.count("\n") == 10  # cut on a line boundary


def test_missing_emoji_renders_as_nothing():
    assert embeds.team_emoji("no_such_team") == ""
    assert embeds.tyre_emoji("SOFT", 2024) == "Soft"


# ------------------------------------------------------------ lookup tables

def test_flags_resolve_for_fixture_data():
    for race in fixture_json("jolpica/races_2024.json")["MRData"]["RaceTable"]["Races"]:
        assert util.country_flag(race["Circuit"]["Location"]["country"]), race["raceName"]
    for d in fixture_json("jolpica/drivers.json")["MRData"]["DriverTable"]["Drivers"]:
        assert util.nationality_flag(d["nationality"]), d["nationality"]
    assert util.country_flag("Abu Dhabi") == util.country_flag("United Arab Emirates") != ""
    assert util.country_flag("Atlantis") == "" and util.nationality_flag(None) == ""


def test_formatting():
    assert util.fmt_lap(89.158) == "1:29.158" and util.fmt_lap(59.9996) == "1:00.000"
    assert util.fmt_points(25.0) == "25" and util.fmt_points(12.5) == "12.5"
    assert util.fold("Pérez") == "perez"


# --------------------------------------------------- shared parameter rules

async def test_year_defaults_and_range(seasons, clock):
    seasons({2026: three_race_season(2026), 2025: three_race_season(2025)})
    clock(datetime(2026, 3, 20, tzinfo=UTC))
    assert await params.resolve_year(None, 1950) == 2026
    clock(datetime(2026, 2, 1, tzinfo=UTC))          # pre-season: nothing run yet this year
    assert await params.resolve_year(None, 1950) == 2025
    for bad in (1949, 2027):
        with pytest.raises(UserError, match="between 1950 and 2026"):
            await params.resolve_year(bad, 1950)


async def test_round_resolution(seasons, clock):
    seasons({2026: three_race_season()})
    clock(datetime(2026, 3, 20, tzinfo=UTC))         # rounds 1 and 2 done, round 3 to come
    assert (await params.resolve_event(2026, None)).round == 2
    assert (await params.resolve_event(2026, "1")).name == "Australian Grand Prix"
    assert (await params.resolve_event(2026, "china")).round == 2
    with pytest.raises(UserError, match="hasn't happened yet"):
        await params.resolve_event(2026, "japan")
    with pytest.raises(UserError, match='Round "mars" not found for 2026'):
        await params.resolve_event(2026, "mars")
    with pytest.raises(UserError, match="has no Sprint session"):
        await params.resolve_event(2026, "1", "Sprint")


async def test_latest_round_of_finished_season_is_the_last_one(seasons, clock):
    seasons({2026: three_race_season()})
    clock(datetime(2026, 12, 1, tzinfo=UTC))
    assert (await params.resolve_event(2026, None)).round == 3


async def test_round_autocomplete(seasons, clock):
    seasons({2026: three_race_season()})
    clock(datetime(2026, 3, 20, tzinfo=UTC))
    assert await params.round_choices(None, "jap") == [("3. Japanese Grand Prix", "3")]
    assert len(await params.round_choices(2026, "")) == 3


# ----------------------------------------------------------------- sources

async def test_500_retries_exactly_once(mock_http):
    calls = mock_http(lambda r: httpx.Response(500))
    with pytest.raises(SourceError) as e:
        await http.get_json("Jolpica", "https://example.test/x")
    assert len(calls) == 2 and e.value.source == "Jolpica"


async def test_404_is_not_retried(mock_http):
    calls = mock_http(lambda r: httpx.Response(404))
    with pytest.raises(SourceError):
        await http.get("X", "https://example.test/x")
    assert len(calls) == 1


async def test_429_waits_then_succeeds(mock_http):
    replies = iter([httpx.Response(429), httpx.Response(200, json={"ok": 1})])
    mock_http(lambda r: next(replies))
    assert await http.get_json("X", "https://example.test/x") == {"ok": 1}


async def test_jolpica_standings_parse_and_cache(mock_http, clock):
    clock(datetime(2026, 6, 1, tzinfo=UTC))
    calls = mock_http(lambda r: httpx.Response(200, json=fixture_json("jolpica/driverstandings_2024.json")))
    first = await jolpica.driver_standings(2024)
    assert first["round"] == 24 and first["rows"][0]["Driver"]["familyName"] == "Verstappen"
    assert await jolpica.driver_standings(2024) == first
    assert len(calls) == 1  # second call served from the cache


async def test_jolpica_merges_races_split_across_pages(mock_http):
    def race(results):
        return {"season": "2026", "round": "1", "raceName": "A", "Results": results}

    def handler(request):
        offset = int(request.url.params["offset"])
        rows = [{"position": str(i)} for i in range(1, 151)][offset:offset + 100]
        return httpx.Response(200, json={"MRData": {"total": "150", "RaceTable": {"Races": [race(rows)]}}})
    mock_http(handler)
    races = await jolpica.season_results(2026)
    assert len(races) == 1 and len(races[0]["Results"]) == 150


async def test_weather_parses_and_skips_missing_days(mock_http):
    mock_http(lambda r: httpx.Response(200, json={"daily": {
        "time": ["2026-10-23", "2026-10-24"], "temperature_2m_min": [14.2, None],
        "temperature_2m_max": [27.9, None], "precipitation_sum": [0.4, None],
        "precipitation_probability_max": [30, None]}}))
    days = await weather.forecast(30.1, -97.6, date(2026, 10, 23), date(2026, 10, 24), "k")
    assert len(days) == 1 and days[0].temp_max == 27.9 and days[0].day == date(2026, 10, 23)


async def test_wikipedia_photo_falls_back_to_none(mock_http):
    mock_http(lambda r: httpx.Response(500))
    assert await wikipedia.photo("https://en.wikipedia.org/wiki/Lewis_Hamilton") is None
    assert await wikipedia.photo(None) is None
    mock_http(lambda r: httpx.Response(200, json={"originalimage": {"source": "https://img/x.jpg"}}))
    assert await wikipedia.photo("https://en.wikipedia.org/wiki/Max_Verstappen") == "https://img/x.jpg"


async def test_concurrent_session_loads_share_one_download(monkeypatch):
    loads = []

    class FakeSession:
        def load(self, **flags):
            loads.append(flags)

    monkeypatch.setattr(fastf1_src.fastf1, "get_session", lambda *a: FakeSession())
    fastf1_src._sessions.clear()
    a, b = await asyncio.gather(fastf1_src.load(2026, 1, "Race", laps=True),
                                fastf1_src.load(2026, 1, "Race", laps=True))
    assert a is b and len(loads) == 1
    await fastf1_src.load(2026, 1, "Race")                    # needs less: reuse
    assert len(loads) == 1
    await fastf1_src.load(2026, 1, "Race", telemetry=True)    # needs more: reload with both
    assert loads[-1] == {"laps": True, "telemetry": True, "weather": False, "messages": False}
    fastf1_src._sessions.clear()


def test_fixtures_are_valid_json():
    for path in FIXTURES.rglob("*.json"):
        json.loads(path.read_text(encoding="utf8"))
