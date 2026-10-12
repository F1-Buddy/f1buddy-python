"""Canaries: each external source, once, against the real service.

Excluded by default. Run with `pytest -m live` to find out whether a site or API has changed shape.
"""
from datetime import timedelta

import pytest

from f1buddy import ctx, util
from f1buddy.cogs import live
from f1buddy.data import info
from f1buddy.render import fia as fia_render
from f1buddy.series import f1
from f1buddy.sources import fastf1_src, fia, http, jolpica, openf1, weather, wikipedia

pytestmark = pytest.mark.live


@pytest.fixture(autouse=True)
def real_services(monkeypatch):
    http.set_client(None)                              # a real client, replacing the test one that refuses
    monkeypatch.setattr(http, "RETRY_DELAY", 2.0)
    monkeypatch.setattr(jolpica, "MIN_INTERVAL", 0.5)
    fastf1_src.init(ctx.config.data_dir)


async def test_fia_listing_parses_and_a_document_renders():
    docs = fia.parse_listing(await fia.fetch_listing())
    assert docs and any(d.published_at for d in docs)
    pages, total = fia_render.render_pages(await fia.fetch_pdf(docs[0].url), max_pages=1)
    assert total >= 1 and pages[0][:4] == b"\x89PNG"


async def test_jolpica():
    year = util.now().year - 1
    standings = await jolpica.driver_standings(year)
    assert standings["round"] > 0 and {"position", "points", "Driver", "Constructors"} <= set(standings["rows"][0])
    races = await jolpica.races(year)
    assert {"lat", "long"} <= set(races[0]["Circuit"]["Location"])
    results = await jolpica.season_results(year)
    assert len(results) == len(races) and {"position", "status", "Driver", "Constructor"} <= set(results[0]["Results"][0])
    assert (await jolpica.season_qualifying(year))[0]["QualifyingResults"]
    assert await jolpica._total("drivers/hamilton/grid/1/results") > 100


async def test_fastf1_schedule_and_results():
    year = util.now().year - 1
    events = await f1.season_schedule(year)
    assert len(events) > 15 and events[0].race and events[0].qualifying
    session = await fastf1_src.load(year, 1, "Race")
    assert {"Abbreviation", "FullName", "TeamId", "Position", "ClassifiedPosition", "Points",
            "GridPosition"} <= set(session.results.columns)
    assert info.race_rows(session.results)[0].position == "1"


async def test_open_meteo():
    today = util.now().date()
    days = await weather.forecast(1.29, 103.86, today, today + timedelta(days=2), "canary")
    assert len(days) == 3 and days[0].temp_max >= days[0].temp_min


async def test_wikipedia_photo():
    assert (await wikipedia.photo("https://en.wikipedia.org/wiki/Lewis_Hamilton")).startswith("https://")


async def test_openf1_recap():
    session = await openf1.latest_session()
    assert {"session_key", "session_name", "date_end", "country_name"} <= set(session)
    data = await openf1.recap(session["session_key"])
    assert data["drivers"] and {"name_acronym", "driver_number"} <= set(data["drivers"][0])
    assert live.recap_embed(session, data, None).title
