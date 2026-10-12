"""Spec 02: information commands."""
import asyncio
from datetime import date, datetime, timedelta
from types import SimpleNamespace

import pandas as pd
import pytest
from discord import app_commands
from discord.ext import commands

from f1buddy import ctx
from f1buddy.cogs import info as info_cog
from f1buddy.cogs import misc
from f1buddy.data import info
from f1buddy.errors import SourceError, UserError
from f1buddy.render import embeds
from f1buddy.series import f1
from f1buddy.sources import fastf1_src, jolpica, weather, wikipedia
from f1buddy.sources.weather import DayForecast

from conftest import UTC, FakeInteraction, fixture_json, make_event, three_race_season

MID_SEASON = datetime(2026, 3, 20, tzinfo=UTC)   # rounds 1-2 done, round 3 on 29 March


def field(embed, name):
    return next(f.value for f in embed.fields if f.name == name)


def lines(embed, name):
    return field(embed, name).strip().split("\n")


# ---------------------------------------------------------------- schedule

@pytest.fixture
def no_circuit(monkeypatch):
    async def races(year):
        return [{"round": "3", "Circuit": {"circuitId": "suzuka", "Location": {"lat": "34.8", "long": "136.5"}}}]
    monkeypatch.setattr(jolpica, "races", races)


async def test_schedule_shows_next_event(seasons, clock, no_circuit):
    seasons({2026: three_race_season()})
    clock(MID_SEASON)
    embed = embeds.schedule(await info.schedule())
    assert "Japanese GP" in embed.title and "🇯🇵" in embed.title
    assert lines(embed, "Session") == [":one: Practice 1", ":two: Practice 2", ":three: Practice 3",
                                        ":stopwatch: Qualifying", ":checkered_flag: Race"]
    race = int(datetime(2026, 3, 29, 5, tzinfo=UTC).timestamp())
    assert lines(embed, "Time")[-1] == f"<t:{race}:f>" and embed.description == f"Race is <t:{race}:R>!"
    assert embed.footer.text == "Weather forecast available within 72 hours of race"


async def test_schedule_keeps_current_weekend_during_the_race(seasons, clock, no_circuit):
    seasons({2026: three_race_season()})
    china = datetime(2026, 3, 15, 7, tzinfo=UTC)
    clock(china + timedelta(hours=1))
    assert (await info.schedule()).event.round == 2
    clock(china + timedelta(hours=4))
    assert (await info.schedule()).event.round == 3


@pytest.mark.parametrize("fmt,expected", [
    ("sprint_2021", [":one:", ":stopwatch:", ":two:", ":race_car:", ":checkered_flag:"]),
    ("sprint_2023", [":one:", ":stopwatch:", ":stopwatch:", ":race_car:", ":checkered_flag:"]),
    ("sprint_2024", [":one:", ":stopwatch:", ":race_car:", ":stopwatch:", ":checkered_flag:"]),
])
def test_schedule_sprint_emojis(fmt, expected):
    event = make_event(2026, 1, "Chinese Grand Prix", "China", datetime(2026, 3, 15, 7, tzinfo=UTC), fmt)
    embed = embeds.schedule(info.ScheduleView(event))
    assert [l.split()[0] for l in lines(embed, "Session")] == expected


async def test_schedule_weather_within_72_hours(seasons, clock, no_circuit, monkeypatch):
    seasons({2026: three_race_season()})
    clock(datetime(2026, 3, 27, 12, tzinfo=UTC))    # a Friday, 41 h before the race

    async def forecast(lat, lon, start, end, key):
        assert (start, end) == (date(2026, 3, 27), date(2026, 3, 29))
        return [DayForecast(date(2026, 3, 27) + timedelta(days=i), 10 + i, 20 + i, 1.5, 40) for i in range(3)]
    monkeypatch.setattr(weather, "forecast", forecast)
    embed = embeds.schedule(await info.schedule())
    assert lines(embed, "Day") == ["Friday", "Saturday", "Sunday"]
    assert lines(embed, "Temperature")[0] == "10–20 °C" and lines(embed, "Precipitation")[0] == "1.5 mm (40%)"


async def test_schedule_survives_weather_failure(seasons, clock, no_circuit, monkeypatch):
    seasons({2026: three_race_season()})
    clock(datetime(2026, 3, 27, 12, tzinfo=UTC))

    async def boom(*a):
        raise SourceError("Open-Meteo", "down")
    monkeypatch.setattr(weather, "forecast", boom)
    embed = embeds.schedule(await info.schedule())
    assert len(embed.fields) == 2 and "within 72 hours" in embed.footer.text


async def test_schedule_offseason_and_next_year(seasons, clock, no_circuit):
    clock(datetime(2026, 12, 20, tzinfo=UTC))
    seasons({2026: three_race_season()})
    embed = embeds.schedule(await info.schedule())
    assert embed.title == "Race Schedule" and "off season" in embed.description
    assert embed.image.url in embeds.OFFSEASON_GIFS
    seasons({2026: three_race_season(), 2027: three_race_season(2027)})
    view = await info.schedule()
    assert (view.event.year, view.event.round) == (2027, 1)


async def test_schedule_command_attaches_cached_circuit(seasons, clock, no_circuit, interaction):
    seasons({2026: three_race_season()})
    clock(MID_SEASON)
    info.circuit_path("suzuka").write_bytes(b"png")
    await info_cog.Info().schedule.callback(info_cog.Info(), interaction)
    reply = interaction.followup.sent[0]
    assert interaction.response.deferred and reply["file"].filename == "circuit.png"
    assert reply["embed"].image.url == "attachment://circuit.png"


# --------------------------------------------------------------- standings

def standings_rows(n):
    return [{"position": str(i), "points": str(100 - i), "Driver": {"givenName": f"Given{i}", "familyName": f"Family{i}"},
             "Constructors": [{"constructorId": "old_team"}, {"constructorId": "new_team"}]} for i in range(1, n + 1)]


@pytest.fixture
def driver_table(monkeypatch):
    def install(n, round=3):
        async def standings(year, round_=None):
            return {"round": round, "rows": standings_rows(n)}
        monkeypatch.setattr(jolpica, "driver_standings", standings)
    return install


async def test_wdc_full_names_and_crown(seasons, clock, driver_table, monkeypatch):
    seasons({2026: three_race_season()})
    clock(datetime(2026, 12, 1, tzinfo=UTC))
    monkeypatch.setitem(embeds.EMOJIS, "new_team", "<:new_team:1>")
    driver_table(20)
    embed = embeds.wdc(await info.driver_standings(None))
    assert embed.title == "2026 Driver Standings"
    assert [len(lines(embed, n)) for n in ("Position", "Driver", "Points")] == [20, 20, 20]
    # latest team's emoji, full name, and the crown because all 3 rounds are done
    assert lines(embed, "Driver")[0] == "<:new_team:1> Given1 Family1 :crown:"
    assert lines(embed, "Points")[0] == "99"


async def test_wdc_no_crown_mid_season(seasons, clock, driver_table):
    seasons({2026: three_race_season()})
    clock(MID_SEASON)
    driver_table(20, round=2)
    assert ":crown:" not in field(embeds.wdc(await info.driver_standings(None)), "Driver")


async def test_wdc_shortens_names_for_big_grids(seasons, clock, driver_table):
    seasons({2026: three_race_season()})
    clock(MID_SEASON)
    driver_table(30)
    embed = embeds.wdc(await info.driver_standings(1955))
    assert lines(embed, "Driver")[1] == "Family2"
    assert all(len(f.value) <= 1024 for f in embed.fields)
    driver_table(24)
    assert lines(embeds.wdc(await info.driver_standings(1955)), "Driver")[1] == "G. Family2"


async def test_standings_year_limits(seasons, clock):
    seasons({2026: three_race_season()})
    clock(MID_SEASON)
    for year in (1949, 2027):
        with pytest.raises(UserError, match="between 1950 and 2026"):
            await info.driver_standings(year)
    with pytest.raises(UserError, match="1958 was the first season"):
        await info.constructor_standings(1957)


async def test_wcc_2007_exclusion_comes_from_the_data(clock, mock_http):
    import httpx
    clock(MID_SEASON)
    mock_http(lambda r: httpx.Response(200, json=fixture_json("jolpica/constructorstandings_2007.json")))
    embed = embeds.wcc(await info.constructor_standings(2007))
    teams, positions = lines(embed, "Team"), lines(embed, "Position")
    assert positions[teams.index("McLaren")] == "EX"
    assert teams[0] == "Ferrari :crown:" and positions[:3] == ["1", "2", "3"]


# ------------------------------------------------------------ constructors

async def test_constructors(seasons, clock, monkeypatch):
    seasons({2026: three_race_season()})
    clock(MID_SEASON)

    async def teams(year):
        return [{"constructorId": "ferrari", "name": "Ferrari", "url": "https://w/Ferrari", "nationality": "Italian"},
                {"constructorId": "moon", "name": "Moon F1", "url": "", "nationality": "Lunar"}]

    async def standings(year, round=None):
        winner = "ferrari" if year % 2 else "moon"
        return {"round": 1, "rows": [{"position": "1", "Constructor": {"constructorId": winner}}]}
    monkeypatch.setattr(jolpica, "constructors", teams)
    monkeypatch.setattr(jolpica, "constructor_standings", standings)
    embed = embeds.constructors(*await info.constructors(None))
    assert embed.title == "2026 Constructor Information"
    assert lines(embed, "Team") == ["[Ferrari](https://w/Ferrari)", "Moon F1"]
    assert lines(embed, "Nationality") == ["🇮🇹 Italian", "Lunar"]          # unknown nationality: no flag
    odd = len([y for y in range(1958, 2026) if y % 2])
    assert lines(embed, "Championships") == [str(odd), str(68 - odd)]


async def test_constructors_empty_season(seasons, clock, monkeypatch):
    seasons({2026: three_race_season()})
    clock(MID_SEASON)

    async def none(year):
        return []
    monkeypatch.setattr(jolpica, "constructors", none)
    with pytest.raises(UserError, match="No constructor data for 2026"):
        await info.constructors(None)


# ------------------------------------------------------------------ driver

DRIVERS = [
    {"driverId": "hamilton", "code": "HAM", "givenName": "Lewis", "familyName": "Hamilton",
     "dateOfBirth": "1985-01-07", "nationality": "British", "url": "https://en.wikipedia.org/wiki/Lewis_Hamilton"},
    {"driverId": "perez", "code": "PER", "givenName": "Sergio", "familyName": "Pérez", "dateOfBirth": "1990-01-26"},
    {"driverId": "michael_schumacher", "code": "MSC", "givenName": "Michael", "familyName": "Schumacher",
     "dateOfBirth": "1969-01-03"},
    {"driverId": "ralf_schumacher", "code": "SCH", "givenName": "Ralf", "familyName": "Schumacher",
     "dateOfBirth": "1975-06-30"},
    {"driverId": "max_verstappen", "code": "VER", "givenName": "Max", "familyName": "Verstappen",
     "dateOfBirth": "1997-09-30"},
    {"driverId": "verstappen", "givenName": "Jos", "familyName": "Verstappen", "dateOfBirth": "1972-03-04"},
]
CAREER = {"seasons": 20, "active": True, "championships": 12, "entries": 397, "starts": 396, "wins": 106,
          "podiums": 203, "points": 5018.5, "poles": 104, "fastest_laps": 68}


@pytest.fixture
def driver_sources(monkeypatch):
    async def all_drivers():
        return DRIVERS

    async def career(driver_id):
        return CAREER

    async def photo(url):
        return None
    monkeypatch.setattr(jolpica, "all_drivers", all_drivers)
    monkeypatch.setattr(jolpica, "driver_career", career)
    monkeypatch.setattr(wikipedia, "photo", photo)


async def test_driver_profile_lines(driver_sources):
    embed = embeds.driver(await info.driver_profile("hamilton"))
    assert embed.title == "🇬🇧 Lewis Hamilton" and embed.url.endswith("Lewis_Hamilton")
    assert "**:trophy: Championships:** 12" in embed.description        # two digits, read as a number
    assert "**:chart_with_upwards_trend: Points:** 5018.5" in embed.description
    assert embed.description.count("\n") == 8 and embed.image.url is None   # photo failure: no image


async def test_driver_matching(driver_sources):
    for text in ("hamilton", "HAM", "Lewis Hamilton", "lewis hamilton"):
        assert (await info.driver_profile(text)).name == "Lewis Hamilton"
    assert (await info.driver_profile("perez")).name == "Sergio Pérez"
    with pytest.raises(UserError, match="Ralf Schumacher, Michael Schumacher"):
        await info.driver_profile("Schumacher")
    with pytest.raises(UserError, match='Driver "nobody" not found. Try the full name.'):
        await info.driver_profile("nobody")


async def test_driver_autocomplete_recent_first(driver_sources):
    assert await info.driver_autocomplete("ver") == [("Max Verstappen", "max_verstappen"),
                                                     ("Jos Verstappen", "verstappen")]
    assert len(await info.driver_autocomplete("")) <= 25


async def test_driver_easter_eggs_skip_lookup(interaction):
    cog = info_cog.Info()
    await cog.driver.callback(cog, interaction, "anurag")   # would hit the network if it looked anything up
    assert interaction.followup.sent[0]["embed"].title == "friend anurag"
    assert embeds.easter_egg("saul").title == "saul" and embeds.easter_egg("sauli") is None


async def test_driver_career_from_jolpica(mock_http, clock):
    import httpx
    clock(datetime(2026, 6, 1, tzinfo=UTC))

    def result(pos, text, status, points):
        return {"season": "2025", "round": pos, "Results": [
            {"position": pos, "positionText": text, "status": status, "points": points}]}

    def handler(request):
        path = request.url.path
        if path.endswith("/seasons.json"):
            return httpx.Response(200, json={"MRData": {"total": "2", "SeasonTable": {"Seasons": [
                {"season": "2024"}, {"season": "2025"}]}}})
        if path.endswith("drivers/x/results.json"):
            races = [result("1", "1", "Finished", "25"), result("3", "3", "Finished", "15"),
                     result("18", "R", "Engine", "0"), result("20", "W", "Withdrew", "0")]
            return httpx.Response(200, json={"MRData": {"total": "4", "RaceTable": {"Races": races}}})
        if path.endswith("/sprint.json"):
            return httpx.Response(200, json={"MRData": {"total": "1", "RaceTable": {"Races": [
                {"season": "2025", "round": "2", "SprintResults": [{"position": "1", "points": "8"}]}]}}})
        if "driverstandings" in path:
            champion = "x" if "/2024/" in path else "other"
            return httpx.Response(200, json={"MRData": {"StandingsTable": {"StandingsLists": [
                {"round": "24", "DriverStandings": [{"position": "1", "Driver": {"driverId": champion}}]}]}}})
        return httpx.Response(200, json={"MRData": {"total": "7" if "grid" in path else "3"}})
    mock_http(handler)
    career = await jolpica.driver_career("x")
    assert career == {"seasons": 2, "active": False, "championships": 1, "entries": 4, "starts": 3, "wins": 1,
                      "podiums": 2, "points": 48.0, "poles": 7, "fastest_laps": 3}


# ----------------------------------------------------------------- results

def results_frame():
    rows = [
        ("VER", "Max Verstappen", "red_bull", 1.0, "1", 25.0, "0:01:29.1", "0:01:29.5", "0:01:30.0"),
        ("LEC", "Charles Leclerc", "ferrari", 2.0, "2", 18.0, "0:01:29.2", "0:01:29.6", "0:01:30.1"),
        ("NOR", "Lando Norris", "mclaren", 3.0, "3", 15.0, None, "0:01:29.7", "0:01:30.2"),
        ("HAM", "Lewis Hamilton", "ferrari", 4.0, "R", 0.0, None, None, "0:01:30.3"),
        ("ALO", "Fernando Alonso", "aston_martin", 5.0, "D", 0.0, None, None, None),
    ]
    df = pd.DataFrame(rows, columns=["Abbreviation", "FullName", "TeamId", "Position", "ClassifiedPosition",
                                     "Points", "Q3", "Q2", "Q1"])
    for q in ("Q1", "Q2", "Q3"):
        df[q] = pd.to_timedelta(df[q])
    return df.sample(frac=1, random_state=1)   # shuffled: ordering must come from Position


@pytest.fixture
def fake_load(monkeypatch):
    requested = []

    async def load(year, round, name, **flags):
        requested.append((year, round, name))
        laps = pd.DataFrame({
            "Driver": ["VER", "VER", "NOR"], "LapTime": pd.to_timedelta(["0:01:31.0", None, "0:01:30.5"]),
            "Compound": ["HARD", "HARD", "SOFT"], "TyreLife": [12.0, 13.0, 3.0]})
        return SimpleNamespace(results=results_frame(), laps=laps)
    monkeypatch.setattr(fastf1_src, "load", load)
    return requested


async def test_results(seasons, clock, fake_load):
    seasons({2026: three_race_season()})
    clock(MID_SEASON)
    embed = embeds.results(await info.race_results(None, None))
    assert embed.title == "2026 Chinese Grand Prix Race Results" and fake_load == [(2026, 2, "Race")]
    assert lines(embed, "Position") == ["🥇", "🥈", "🥉", "DNF", "DSQ"]
    assert lines(embed, "Driver")[0] == "Max Verstappen" and lines(embed, "Points")[:2] == ["25", "18"]


async def test_results_defaults_and_errors(seasons, clock, fake_load):
    seasons({2026: three_race_season(), 2025: three_race_season(2025)})
    clock(datetime(2026, 2, 1, tzinfo=UTC))        # pre-season
    assert (await info.race_results(None, None)).event_name == "Japanese Grand Prix"
    assert fake_load[-1] == (2025, 3, "Race")      # last season's final race
    clock(MID_SEASON)
    with pytest.raises(UserError, match="That race hasn't happened yet."):
        await info.race_results(2026, "3")
    with pytest.raises(UserError, match='Round "atlantis" not found for 2026.'):
        await info.race_results(2026, "atlantis")


async def test_qualifying(seasons, clock, fake_load):
    seasons({2026: three_race_season()})
    clock(MID_SEASON)
    embed = embeds.results(await info.qualifying_results(None, None), "Qualifying")
    assert embed.title == "2026 Chinese Grand Prix Qualifying Results"
    assert lines(embed, "Time") == ["Q3: 1:29.100", "Q3: 1:29.200", "Q2: 1:29.700", "Q1: 1:30.300", "No time"]
    assert lines(embed, "Position") == ["1", "2", "3", "4", "5"]
    assert fake_load == [(2026, 2, "Qualifying")]   # sprint weekend: Grand Prix qualifying, not the sprint one


async def test_qualifying_can_be_ahead_of_the_race(seasons, clock, fake_load):
    seasons({2026: three_race_season()})
    clock(datetime(2026, 3, 28, 12, tzinfo=UTC))   # Japan qualifying done, race tomorrow
    assert (await info.qualifying_results(None, None)).event_name == "Japanese Grand Prix"
    assert (await info.race_results(None, None)).event_name == "Chinese Grand Prix"


# ------------------------------------------------------------- fastest lap

async def test_fl_single_round(seasons, clock, fake_load):
    seasons({2026: three_race_season()})
    clock(MID_SEASON)
    year, rows = await info.fastest_laps(None, "1")
    assert rows == [{"code": "NOR", "team_id": "mclaren", "seconds": 90.5, "compound": "SOFT", "tyre_life": 3,
                     "event": "Australian Grand Prix", "country": "Australia"}]
    embed = embeds.fastest_laps(year, rows)[0]
    assert lines(embed, "GP") == ["🇦🇺 NOR"] and lines(embed, "Laptime") == ["1:30.500"]
    assert lines(embed, "Tyre") == ["Soft 3 laps"]


async def test_fl_season_uses_cache_and_splits_embeds(seasons, clock, monkeypatch):
    events = [make_event(2025, n, f"GP{n} Grand Prix", "Italy", datetime(2025, 3, 1, tzinfo=UTC) + timedelta(weeks=n))
              for n in range(1, 25)]
    seasons({2025: events, 2026: []})
    clock(datetime(2026, 1, 10, tzinfo=UTC))
    for e in events:
        await ctx.db.cache_set(f"fl:2025:{e.round}", {"code": "VER", "team_id": "x", "seconds": 80.0,
                                                      "compound": "HARD", "tyre_life": 5, "event": e.name,
                                                      "country": e.country})

    async def no_load(*a, **k):
        raise AssertionError("cached rounds must not load a session")
    monkeypatch.setattr(fastf1_src, "load", no_load)
    year, rows = await info.fastest_laps(None, None)
    out = embeds.fastest_laps(year, rows)
    assert year == 2025 and len(rows) == 24            # final round of a finished season included
    assert [e.title for e in out] == ["Fastest Lap 2025", "Fastest Lap 2025 Continued"]
    assert [len(lines(e, "GP")) for e in out] == [10, 14]


async def test_fl_one_failing_round_is_listed_unavailable(seasons, clock, monkeypatch, fake_load):
    seasons({2026: three_race_season()})
    clock(MID_SEASON)
    good = fastf1_src.load

    async def flaky(year, round, name, **flags):
        if round == 1:
            raise SourceError("FastF1", "no data")
        return await good(year, round, name, **flags)
    monkeypatch.setattr(fastf1_src, "load", flaky)
    year, rows = await info.fastest_laps(2026, None)
    assert rows[0] == {"event": "Australian Grand Prix", "country": "Australia", "error": True}
    assert rows[1]["code"] == "NOR"
    assert lines(embeds.fastest_laps(year, rows)[0], "GP")[0] == "🇦🇺 Australian Grand Prix — unavailable"
    assert await ctx.db.cache_get("fl:2026:1") is None  # a failure is not cached


async def test_fl_errors(seasons, clock):
    seasons({2026: three_race_season()})
    clock(MID_SEASON)
    with pytest.raises(UserError, match="between 2018 and 2026"):
        await info.fastest_laps(2017, None)
    with pytest.raises(UserError, match="hasn't happened yet"):
        await info.fastest_laps(2026, "3")


# -------------------------------------------------------------------- help

def build_tree():
    class Client:
        pass
    bot = commands.Bot(command_prefix="f1$", intents=__import__("discord").Intents.none())
    return bot


async def loaded_bot():
    from f1buddy.bot import COGS
    bot = build_tree()
    bot.config = ctx.config
    for name in COGS:
        await bot.load_extension(f"f1buddy.cogs.{name}")
    return bot


async def test_help_lists_every_command_once_with_descriptions():
    bot = await loaded_bot()
    cmds = misc.leaf_commands(bot.tree)
    text = "\n".join(f.value for f in misc.help_overview(bot.tree).fields)
    for cmd in cmds:
        assert text.count(f"`/{cmd.qualified_name}` —") == 1, cmd.qualified_name
        assert cmd.description and cmd.description != "…", cmd.qualified_name
        for p in cmd.parameters:
            assert p.description and p.description != "…", f"{cmd.qualified_name}.{p.name}"
    names = {c.qualified_name for c in cmds}
    legacy = {"schedule", "wdc", "wcc", "constructors", "driver", "results", "qualifying", "fl", "fiadoc",
              "laptimes", "positions", "strategy", "qualigap", "consistency", "telemetry", "trackdominance",
              "avgpos", "h2h", "lightsout", "help"}
    assert legacy <= names
    await bot.close()


async def test_help_detail_and_unknown():
    bot = await loaded_bot()
    embed, shot = misc.help_detail(bot.tree, "results")
    assert embed.title == "f1buddy Help - results" and shot.name == "results.png"
    body = embed.description.split("\n")
    assert body[2].startswith("`round` (optional)") and body[3].startswith("`year` (optional)")
    embed, shot = misc.help_detail(bot.tree, "lightsout")
    assert embed is not None and shot is None          # no screenshot: no image, no error
    assert misc.help_detail(bot.tree, "nope") == (None, None)
    await bot.close()


# --------------------------------------------------------------- lightsout

class FakeMessage:
    id = 555

    def __init__(self):
        self.edits = []

    async def add_reaction(self, emoji):
        pass

    async def edit(self, embed):
        self.edits.append((embed.title, embed.description))


class FakeBot:
    def __init__(self):
        self.listener = None
        self.config = ctx.config

    def add_listener(self, fn, name):
        self.listener = fn

    def remove_listener(self, fn, name):
        self.listener = None


def user(uid, bot=False):
    return SimpleNamespace(id=uid, bot=bot, mention=f"<@{uid}>")


def reaction(message_id, emoji=misc.CAR):
    return SimpleNamespace(message=SimpleNamespace(id=message_id), emoji=emoji)


async def start_game(**kwargs):
    bot, message = FakeBot(), FakeMessage()
    interaction = FakeInteraction()

    async def send(**kw):
        return message
    interaction.followup.send = send
    task = asyncio.create_task(misc.Misc(bot).play(interaction, step=0, **kwargs))
    return bot, message, task


async def wait_for_lights_out(message):
    while not any(":green_square:" in d for _, d in message.edits):
        await asyncio.sleep(0)


async def test_lightsout_winner_ignores_other_messages_bots_and_jump_starts():
    bot, message, task = await start_game(delay=0.05, timeout=5)
    await asyncio.sleep(0)
    await bot.listener(reaction(555), user(1))            # before lights out: jump start
    await wait_for_lights_out(message)
    await bot.listener(reaction(999), user(2))            # another message
    await bot.listener(reaction(555), user(3, bot=True))  # a bot
    await bot.listener(reaction(555), user(1))            # the jump-starter again
    assert not task.done()
    await bot.listener(reaction(555), user(4))
    embed = await task
    assert embed.title == "And away we go!" and "<@4> got away the fastest!" in embed.description
    assert "Jump start: <@1>" in embed.description
    assert embed.footer.text.startswith("Lights held for 0.05 seconds · reacted in ")
    assert bot.listener is None


async def test_lightsout_times_out():
    bot, message, task = await start_game(delay=0, timeout=0.01)
    embed = await task
    assert embed.title == "No one got away" and bot.listener is None
    assert sum(":red_circle:" in d for _, d in message.edits) == 5   # the five light steps


# -------------------------------------------------------------------- sync

async def test_sync_admin_only():
    synced = []

    class Tree:
        async def sync(self):
            synced.append(1)
            return ["a", "b", "c"]

    async def change_presence(activity):
        assert "V10s | /help | 2 servers" == activity.name
    bot = SimpleNamespace(config=ctx.config, tree=Tree(), guilds=[1, 2], change_presence=change_presence)
    cog = misc.Misc(bot)
    said = []

    def context(uid):
        async def send(text):
            said.append(text)
        return SimpleNamespace(author=SimpleNamespace(id=uid, display_name="bob", mention=f"<@{uid}>"), send=send)
    await cog.sync.callback(cog, context(2))
    assert said == ["bob is not a bot admin! Can't sync :("] and not synced
    await cog.sync.callback(cog, context(1))
    assert said[-1] == "<@1> synced 3 commands" and synced == [1]
