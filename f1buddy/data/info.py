"""Data for the information commands (spec 02). No Discord types here."""
import logging
from dataclasses import dataclass
from datetime import timedelta

import pandas as pd

from .. import ctx, util
from ..errors import SourceError, UserError
from ..series import Event
from ..sources import fastf1_src, jolpica, weather, wikipedia
from . import params

log = logging.getLogger(__name__)

# ---------------------------------------------------------------- schedule


@dataclass(frozen=True)
class ScheduleView:
    event: Event | None                 # None = off season
    forecast: tuple | None = None       # DayForecast per event day, when the race is within 72 h
    circuit_png: bytes | None = None


def next_event(this_year: list[Event], next_year: list[Event], now) -> Event | None:
    """First event whose final session started less than 3 hours ago or is still to come."""
    for event in [*this_year, *next_year]:
        if event.sessions and event.sessions[-1].start_utc + timedelta(hours=3) > now:
            return event
    return None


def circuit_path(circuit_id: str):
    return ctx.config.data_dir / "plots" / f"circuit_{circuit_id}.png"


async def circuit_of(event: Event) -> dict | None:
    """Jolpica's circuit record (id, coordinates) for an event, or None if unavailable."""
    try:
        races = await jolpica.races(event.year)
    except SourceError:
        return None
    race = next((r for r in races if int(r["round"]) == event.round), None)
    return race["Circuit"] if race else None


async def schedule() -> ScheduleView:
    now = util.now()
    this_year = await params.season(now.year)
    try:
        next_year = await params.season(now.year + 1)
    except SourceError:
        next_year = []
    event = next_event(this_year, next_year, now)
    if event is None:
        return ScheduleView(None)

    circuit = await circuit_of(event)
    forecast, png = None, None
    if circuit:
        path = circuit_path(circuit["circuitId"])
        if path.exists():
            png = path.read_bytes()
        race = event.race
        if race and timedelta(0) <= race.start_utc - now <= timedelta(hours=72):
            try:
                loc = circuit["Location"]
                forecast = tuple(await weather.forecast(
                    loc["lat"], loc["long"], event.sessions[0].start_utc.date(), race.start_utc.date(),
                    f"{event.year}:{event.round}")) or None
            except (SourceError, KeyError) as e:
                log.warning("weather unavailable: %s", e)
    return ScheduleView(event, forecast, png)


# --------------------------------------------------------------- standings


@dataclass(frozen=True)
class StandingRow:
    position: str
    name: str
    team_id: str
    points: float
    given: str = ""
    family: str = ""


@dataclass(frozen=True)
class Standings:
    year: int
    rows: tuple
    complete: bool      # final round has been run, so the leader is the champion


async def _complete(year, standings_round) -> bool:
    if year < util.now().year:
        return True
    return standings_round > 0 and standings_round >= len(await params.season(year))


def _position(row) -> str:
    # an excluded entrant (McLaren 2007) has no numeric position
    return row["position"] if str(row.get("position", "")).isdigit() else "EX"


async def driver_standings(year: int | None) -> Standings:
    year = await resolve_standings_year(year, 1950)
    data = await jolpica.driver_standings(year)
    if not data["rows"]:
        raise UserError(f"No driver standings for {year} yet.")
    rows = tuple(
        StandingRow(_position(r), f"{r['Driver']['givenName']} {r['Driver']['familyName']}",
                    r["Constructors"][-1]["constructorId"] if r.get("Constructors") else "",
                    float(r["points"]), r["Driver"]["givenName"], r["Driver"]["familyName"])
        for r in data["rows"])
    return Standings(year, rows, await _complete(year, data["round"]))


async def constructor_standings(year: int | None) -> Standings:
    year = await resolve_standings_year(year, 1958)
    data = await jolpica.constructor_standings(year)
    if not data["rows"]:
        raise UserError(f"No constructor standings for {year} yet.")
    rows = tuple(StandingRow(_position(r), r["Constructor"]["name"], r["Constructor"]["constructorId"],
                             float(r["points"])) for r in data["rows"])
    return Standings(year, rows, await _complete(year, data["round"]))


async def resolve_standings_year(year, min_year):
    if year is not None and year < min_year:
        raise UserError(f"Year must be between {min_year} and {util.now().year}. "
                        f"{min_year} was the first season.")
    return await params.resolve_year(year, min_year)


# ------------------------------------------------------------ constructors


@dataclass(frozen=True)
class ConstructorRow:
    team_id: str
    name: str
    url: str
    nationality: str
    titles: int


async def constructors(year: int | None) -> tuple[int, tuple]:
    year = await params.resolve_year(year, 1950)
    teams = await jolpica.constructors(year)
    if not teams:
        raise UserError(f"No constructor data for {year}.")
    titles = await jolpica.constructor_titles()
    return year, tuple(ConstructorRow(t["constructorId"], t["name"], t.get("url", ""),
                                      t.get("nationality", ""), titles.get(t["constructorId"], 0))
                       for t in teams)


# ------------------------------------------------------------------ driver


@dataclass(frozen=True)
class DriverProfile:
    name: str
    url: str
    nationality: str
    photo: str | None
    career: dict


def _full(d):
    return f"{d['givenName']} {d['familyName']}"


def _recent_first(drivers):
    return sorted(drivers, key=lambda d: d.get("dateOfBirth", ""), reverse=True)


def match_drivers(drivers: list[dict], text: str) -> list[dict]:
    """Drivers whose id, full name, surname or code equals the text (case and accents ignored)."""
    needle = util.fold(text)
    by_id = [d for d in drivers if d["driverId"] == text]
    if by_id:
        return by_id
    full = [d for d in drivers if util.fold(_full(d)) == needle]
    if full:
        return full
    return [d for d in drivers if needle and needle in (util.fold(d["familyName"]), util.fold(d.get("code", "")))]


async def driver_profile(text: str) -> DriverProfile:
    matches = _recent_first(match_drivers(await jolpica.all_drivers(), text))
    if not matches:
        raise UserError(f'Driver "{text}" not found. Try the full name.')
    if len(matches) > 1:
        names = ", ".join(_full(d) for d in matches[:5])
        raise UserError(f'"{text}" matches more than one driver: {names}. Use the full name.')
    d = matches[0]
    career = await jolpica.driver_career(d["driverId"])
    return DriverProfile(_full(d), d.get("url", ""), d.get("nationality", ""),
                         await wikipedia.photo(d.get("url")), career)


async def driver_autocomplete(current: str) -> list[tuple[str, str]]:
    try:
        drivers = await jolpica.all_drivers()
    except SourceError:
        return []
    needle = util.fold(current)
    hits = [d for d in drivers if needle in util.fold(_full(d))]
    return [(_full(d), d["driverId"]) for d in _recent_first(hits)[:25]]


# ----------------------------------------------------------------- results


@dataclass(frozen=True)
class ResultRow:
    position: str
    name: str
    team_id: str
    value: str      # points, or the qualifying time


@dataclass(frozen=True)
class ResultView:
    year: int
    event_name: str
    rows: tuple


STATUS = {"R": "DNF", "D": "DSQ", "E": "EX", "W": "WD", "F": "DNQ", "N": "NC"}


def _name(row):
    full = row.get("FullName")
    return full if isinstance(full, str) and full else str(row.get("Abbreviation", "?"))


def race_rows(results: pd.DataFrame) -> tuple:
    rows = []
    for _, r in results.sort_values("Position", na_position="last").iterrows():
        classified = str(r.get("ClassifiedPosition", "") or "")
        if classified.isdigit():
            position = classified
        elif classified in STATUS:
            position = STATUS[classified]
        elif pd.notna(r.get("Position")):
            position = str(int(r["Position"]))
        else:
            position = "–"
        points = r.get("Points")
        rows.append(ResultRow(position, _name(r), str(r.get("TeamId", "") or ""),
                              util.fmt_points(points) if pd.notna(points) else "0"))
    return tuple(rows)


def quali_rows(results: pd.DataFrame) -> tuple:
    rows = []
    for _, r in results.sort_values("Position", na_position="last").iterrows():
        time = "No time"
        for segment in ("Q3", "Q2", "Q1"):
            value = r.get(segment)
            if pd.notna(value):
                time = f"{segment}: {util.fmt_lap(value.total_seconds())}"
                break
        position = str(int(r["Position"])) if pd.notna(r.get("Position")) else "–"
        rows.append(ResultRow(position, _name(r), str(r.get("TeamId", "") or ""), time))
    return tuple(rows)


async def _results(year, round, min_year, kind, to_rows) -> ResultView:
    year, event = await params.resolve(year, round, min_year, kind)
    session = await fastf1_src.load(year, event.round, kind)
    if session.results is None or session.results.empty:
        raise UserError(f"No {kind.lower()} results are available for {year} {event.name}.")
    return ResultView(year, event.name, to_rows(session.results))


async def race_results(year, round) -> ResultView:
    return await _results(year, round, 1950, "Race", race_rows)


async def sprint_results(year, round) -> ResultView:
    return await _results(year, round, 2021, "Sprint", race_rows)


async def qualifying_results(year, round) -> ResultView:
    return await _results(year, round, 1994, "Qualifying", quali_rows)


# ------------------------------------------------------------- fastest lap


def fastest_from(laps: pd.DataFrame, results: pd.DataFrame) -> dict | None:
    """The fastest timed lap of a session as a plain dict, or None if there are no timed laps."""
    timed = laps[laps["LapTime"].notna()]
    if timed.empty:
        return None
    lap = timed.loc[timed["LapTime"].idxmin()]
    team = results.loc[results["Abbreviation"] == lap["Driver"], "TeamId"]
    return {
        "code": lap["Driver"],
        "team_id": str(team.iloc[0]) if len(team) else "",
        "seconds": lap["LapTime"].total_seconds(),
        "compound": str(lap.get("Compound") or "UNKNOWN"),
        "tyre_life": int(lap["TyreLife"]) if pd.notna(lap.get("TyreLife")) else None,
    }


async def fastest_lap(event: Event) -> dict:
    """Fastest race lap for one event; stored forever once computed."""
    key = f"fl:{event.year}:{event.round}"
    hit = await ctx.db.cache_get(key)
    if hit is not None:
        return hit
    session = await fastf1_src.load(event.year, event.round, "Race", laps=True)
    lap = fastest_from(session.laps, session.results)
    if lap is None:
        raise SourceError("FastF1", f"no timed laps for {key}")
    lap.update(event=event.name, country=event.country)
    await ctx.db.cache_set(key, lap)
    return lap


async def fastest_laps(year: int | None, round: str | None) -> tuple[int, list[dict]]:
    """One row per requested round. A round that fails to load is a row with 'error'."""
    year = await params.resolve_year(year, 2018)
    if round is not None and str(round).strip():
        events = [await params.resolve_event(year, round)]
    else:
        events = params.completed(await params.season(year), "Race")
        if not events:
            raise UserError(f"No race has been run yet in {year}.")
    rows = []
    for event in events:
        try:
            rows.append(await fastest_lap(event))
        except SourceError as e:
            log.warning("fastest lap unavailable: %s", e)
            rows.append({"event": event.name, "country": event.country, "error": True})
    return year, rows
