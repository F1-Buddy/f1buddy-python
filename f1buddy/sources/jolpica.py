"""Jolpica (the Ergast successor). Returns Ergast-shaped dicts, cached in SQLite."""
import asyncio
import time

from .. import ctx, util
from . import http

BASE = "https://api.jolpi.ca/ergast/f1"
MIN_INTERVAL = 0.5  # Jolpica allows 4 requests per second, but throttles bursts; tests set this to 0
_lock = asyncio.Lock()
_last = 0.0
HOUR, DAY = 3600, 86400


async def _get(path, **params):
    global _last
    async with _lock:
        wait = _last + MIN_INTERVAL - time.monotonic()
        if wait > 0:
            await asyncio.sleep(wait)
        try:
            data = await http.get_json("Jolpica", f"{BASE}/{path}.json", params or None)
        finally:
            _last = time.monotonic()
    return data["MRData"]


async def _total(path) -> int:
    return int((await _get(path, limit=1))["total"])


async def _pages(path):
    offset = 0
    while True:
        data = await _get(path, limit=100, offset=offset)
        yield data
        offset += 100
        if offset >= int(data["total"]):
            return


async def _races(path, key):
    """All pages of a race-table query, merging races that were split across pages."""
    races = {}
    async for data in _pages(path):
        for race in data["RaceTable"]["Races"]:
            ident = (race["season"], race["round"])
            if ident in races:
                races[ident][key].extend(race[key])
            else:
                races[ident] = race
    return list(races.values())


async def _cached(key, ttl, factory):
    hit = await ctx.db.cache_get(key)
    if hit is not None:
        return hit
    value = await factory()
    await ctx.db.cache_set(key, value, ttl)
    return value


def _ttl(year):
    """Past seasons never change; the current one is refreshed hourly."""
    return None if int(year) < util.now().year else HOUR


async def _standings(kind, list_key, year, round):
    path = f"{year}/{round}/{kind}" if round else f"{year}/{kind}"
    lists = (await _get(path, limit=100))["StandingsTable"]["StandingsLists"]
    if not lists:
        return {"round": 0, "rows": []}
    return {"round": int(lists[0]["round"]), "rows": lists[0][list_key]}


async def driver_standings(year, round=None):
    return await _cached(f"jol:ds:{year}:{round or 'last'}", _ttl(year),
                         lambda: _standings("driverstandings", "DriverStandings", year, round))


async def constructor_standings(year, round=None):
    return await _cached(f"jol:cs:{year}:{round or 'last'}", _ttl(year),
                         lambda: _standings("constructorstandings", "ConstructorStandings", year, round))


async def constructors(year):
    async def fetch():
        return (await _get(f"{year}/constructors", limit=100))["ConstructorTable"]["Constructors"]
    return await _cached(f"jol:constructors:{year}", _ttl(year), fetch)


async def season_drivers(year):
    async def fetch():
        return (await _get(f"{year}/drivers", limit=100))["DriverTable"]["Drivers"]
    return await _cached(f"jol:drivers:{year}", _ttl(year), fetch)


async def races(year):
    async def fetch():
        return (await _get(f"{year}/races", limit=100))["RaceTable"]["Races"]
    return await _cached(f"jol:races:{year}", DAY, fetch)


async def season_results(year):
    return await _cached(f"jol:results:{year}", _ttl(year), lambda: _races(f"{year}/results", "Results"))


async def season_qualifying(year):
    return await _cached(f"jol:quali:{year}", _ttl(year),
                         lambda: _races(f"{year}/qualifying", "QualifyingResults"))


async def all_drivers():
    async def fetch():
        drivers = []
        async for data in _pages("drivers"):
            drivers.extend(data["DriverTable"]["Drivers"])
        return drivers
    return await _cached("jol:all_drivers", 7 * DAY, fetch)


async def constructor_titles():
    """constructorId -> number of constructors' championships won in completed seasons."""
    async def fetch():
        titles = {}
        # ponytail: a title won this season isn't counted until the year ends; add a
        # season-complete check here if that month matters.
        for year in range(1958, util.now().year):
            rows = (await constructor_standings(year))["rows"]
            winner = next((r for r in rows if r.get("position") == "1"), None)
            if winner:
                cid = winner["Constructor"]["constructorId"]
                titles[cid] = titles.get(cid, 0) + 1
        return titles
    return await _cached("jol:constructor_titles", DAY, fetch)


async def driver_career(driver_id):
    async def fetch():
        this_year = util.now().year
        data = await _get(f"drivers/{driver_id}/seasons", limit=100)
        seasons = [int(s["season"]) for s in data["SeasonTable"]["Seasons"]]
        results = [r["Results"][0] for r in await _races(f"drivers/{driver_id}/results", "Results")]
        sprints = []
        if seasons and seasons[-1] >= 2021:
            sprints = [r["SprintResults"][0]
                       for r in await _races(f"drivers/{driver_id}/sprint", "SprintResults")]
        championships = 0
        for year in seasons:
            if year < this_year:
                rows = (await driver_standings(year))["rows"]
                if rows and rows[0].get("position") == "1" and rows[0]["Driver"]["driverId"] == driver_id:
                    championships += 1
        not_started = {"Did not start", "Did not qualify", "Did not prequalify", "Withdrew"}
        fastest = None
        if seasons and seasons[-1] >= 2004:  # Jolpica only has fastest-lap data from 2004
            fastest = await _total(f"drivers/{driver_id}/fastest/1/results")
        return {
            "seasons": len(seasons),
            "active": bool(seasons) and seasons[-1] >= this_year,
            "championships": championships,
            "entries": len(results),
            "starts": sum(1 for r in results if r.get("positionText") not in ("F", "W")
                          and r.get("status") not in not_started),
            "wins": sum(1 for r in results if r.get("position") == "1"),
            "podiums": sum(1 for r in results if r.get("position") in ("1", "2", "3")),
            "points": sum(float(r.get("points", 0)) for r in results + sprints),
            "poles": await _total(f"drivers/{driver_id}/grid/1/results"),
            "fastest_laps": fastest,
        }

    key = f"jol:career:{driver_id}"
    career = await ctx.db.cache_get(key)
    if career is None:
        career = await fetch()
        await ctx.db.cache_set(key, career, DAY if career["active"] else 30 * DAY)
    return career
