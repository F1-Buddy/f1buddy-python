"""Data for the plot commands (spec 03).

`compute_*` functions are pure: plain frames or dicts in, a frozen dataclass out. The async functions
below them resolve parameters, load what is needed, and return (png bytes, embed text) through the plot cache.
"""
import asyncio
import hashlib
import itertools
import logging
import re
from dataclasses import dataclass

import numpy as np
import pandas as pd

from .. import ctx, util
from ..errors import SourceError, UserError
from ..render import style
from ..sources import fastf1_src, jolpica
from . import info, params

log = logging.getLogger(__name__)

COMPOUNDS = {"SOFT": "#da291c", "MEDIUM": "#ffd12e", "HARD": "#f0f0ec", "INTERMEDIATE": "#43b02a",
             "WET": "#0067ad", "UNKNOWN": "#00ffff", "TEST-UNKNOWN": "#434649"}
COMPOUNDS_2018 = {**COMPOUNDS, "SOFT": "yellow", "MEDIUM": "white", "HARD": "#0096FF", "HYPERSOFT": "pink",
                  "ULTRASOFT": "purple", "SUPERSOFT": "red", "SUPERHARD": "orange"}
# A retirement with one of these statuses was not a mechanical failure. Anything else is,
# so a new mechanical status string needs no code change.
DRIVER_CAUSED = {"accident", "collision", "collision damage", "spun off", "disqualified", "did not start",
                 "did not qualify", "withdrew", "illness", "injury", "injured"}
MINI_SECTORS = 25


# ------------------------------------------------------------- dataclasses

@dataclass(frozen=True)
class Line:
    code: str
    colour: str
    x: tuple
    y: tuple
    dashed: bool = False


@dataclass(frozen=True)
class LinesData:            # laptimes and positions
    title: str
    lines: tuple
    total_laps: int
    n_drivers: int = 0
    missing_colour: bool = False


@dataclass(frozen=True)
class StrategyData:
    title: str
    drivers: tuple          # (code, ((compound, laps), ...)) in finishing order
    palette: dict
    total_laps: int


@dataclass(frozen=True)
class QualiGapData:
    title: str
    rows: tuple             # (code, colour, delta seconds | None) in classified order; pole has delta 0
    missing_colour: bool = False


@dataclass(frozen=True)
class ConsistencyData:
    title: str
    code: str
    laps: tuple             # (lap number, seconds, 'fastest' | 'outlier' | 'quicker' | 'slower')
    mean: float
    std: float


@dataclass(frozen=True)
class Trace:
    code: str
    colour: str
    distance: tuple
    speed: tuple
    throttle: tuple
    brake: tuple
    lap_seconds: float


@dataclass(frozen=True)
class TelemetryData:
    title: str
    traces: tuple
    corners: tuple = ()     # (distance, label)
    missing_colour: bool = False


@dataclass(frozen=True)
class DominanceData:
    title: str
    x: tuple
    y: tuple
    point_winner: tuple     # 0 or 1 for each outline point
    sectors: tuple          # winner (0 or 1) of each mini-sector
    drivers: tuple          # ((code, colour), (code, colour))
    rotation: float = 0.0


@dataclass(frozen=True)
class BarsData:             # avgpos
    title: str
    rows: tuple             # (label, value, colour) best first
    x_max: int
    large_labels: bool
    missing_colour: bool = False


@dataclass(frozen=True)
class H2HData:
    title: str
    pairs: tuple            # (team_id, team_name, colour, left_code, left_wins, right_code, right_wins)
    missing_colour: bool = False


@dataclass(frozen=True)
class CircuitData:
    x: tuple
    y: tuple
    rotation: float = 0.0


# ---------------------------------------------------------- pure computing

def _seconds(series):
    return tuple(series.dt.total_seconds())


def _two_colours(colours, a, b):
    first, missing_a = style.colour(colours.get(a))
    second, missing_b = style.colour(colours.get(b))
    return first, style.clash(first, second), missing_a or missing_b


def compute_laptimes(laps, codes, colours, title) -> LinesData:
    first, second, missing = _two_colours(colours, *codes)
    lines = []
    for code, colour in zip(codes, (first, second)):
        d = laps[laps["Driver"] == code].sort_values("LapNumber")
        lines.append(Line(code, colour, tuple(d["LapNumber"].astype(int)), _seconds(d["LapTime"])))
    return LinesData(title, tuple(lines), int(laps["LapNumber"].max()), missing_colour=missing)


def _finishing_order(results):
    return list(results.sort_values("Position", na_position="last")["Abbreviation"])


def compute_positions(laps, results, colours, title) -> LinesData:
    n = len(results)
    lines, seen_teams, missing = [], set(), False
    by_code = results.set_index("Abbreviation")
    for code in _finishing_order(results):
        d = laps[(laps["Driver"] == code) & laps["Position"].notna()].sort_values("LapNumber")
        grid = by_code.at[code, "GridPosition"] if "GridPosition" in by_code else np.nan
        grid = n if pd.isna(grid) or grid < 1 else int(grid)   # a pit-lane start counts as last
        colour, miss = style.colour(colours.get(code))
        missing |= miss
        team = by_code.at[code, "TeamId"] if "TeamId" in by_code else code
        lines.append(Line(code, colour, (0, *d["LapNumber"].astype(int)), (grid, *d["Position"].astype(int)),
                          dashed=team in seen_teams))
        seen_teams.add(team)
    total = int(laps["LapNumber"].max()) if len(laps) else 0
    return LinesData(title, tuple(lines), total, n_drivers=n, missing_colour=missing)


def compute_strategy(laps, results, year, title) -> StrategyData:
    drivers = []
    for code in _finishing_order(results):
        d = laps[laps["Driver"] == code]
        stints = []
        for _, stint in d.groupby("Stint", sort=True):
            named = stint["Compound"].dropna()
            compound = str(named.iloc[0]).upper() if len(named) and str(named.iloc[0]).strip() else "UNKNOWN"
            stints.append((compound, len(stint)))
        drivers.append((code, tuple(stints)))
    palette = COMPOUNDS_2018 if year == 2018 else COMPOUNDS
    return StrategyData(title, tuple(drivers), palette, int(laps["LapNumber"].max()) if len(laps) else 0)


def best_quali_time(row):
    """A driver's time in the last qualifying segment they took part in, in seconds, or None."""
    for segment in ("Q3", "Q2", "Q1"):
        value = row.get(segment)
        if pd.notna(value):
            return value.total_seconds()
    return None


def compute_qualigap(results, colours, title) -> QualiGapData:
    ordered = results.sort_values("Position", na_position="last")
    times = [(r["Abbreviation"], best_quali_time(r)) for _, r in ordered.iterrows()]
    pole = next((t for _, t in times if t is not None), None)
    if pole is None:
        raise UserError("No qualifying times were set in that session.")
    rows, missing = [], False
    for code, t in times:
        colour, miss = style.colour(colours.get(code))
        missing |= miss
        rows.append((code, colour, None if t is None else t - pole))
    return QualiGapData(title, tuple(rows), missing)


def compute_consistency(laps, code, title) -> ConsistencyData:
    d = laps[laps["LapTime"].notna()].sort_values("LapNumber")
    seconds = d["LapTime"].dt.total_seconds()
    excluded = ((d["LapNumber"] == 1) | d["PitInTime"].notna() | d["PitOutTime"].notna()
                | (d["TrackStatus"].astype(str) != "1"))
    if (~excluded).sum():
        excluded |= seconds > 1.07 * seconds[~excluded].median()
    clean = seconds[~excluded]
    if len(clean) < 3:
        raise UserError("Not enough clean laps to measure consistency.")
    mean, std = float(clean.mean()), float(clean.std())
    fastest = seconds.idxmin()
    out = []
    for idx, row in d.iterrows():
        t = seconds[idx]
        kind = ("fastest" if idx == fastest else "outlier" if excluded[idx]
                else "quicker" if t <= mean else "slower")
        out.append((int(row["LapNumber"]), float(t), kind))
    return ConsistencyData(title, code, tuple(out), mean, std)


def compute_dominance(pos1, pos2, drivers, title, rotation=0.0) -> DominanceData:
    """Split the lap into 25 equal parts by distance; the higher mean speed wins each part."""
    def sector_of(pos):
        fraction = pos["Distance"] / pos["Distance"].max()
        return np.minimum((fraction * MINI_SECTORS).astype(int), MINI_SECTORS - 1)

    s1, s2 = sector_of(pos1), sector_of(pos2)
    mean1 = pos1["Speed"].groupby(s1.values).mean().reindex(range(MINI_SECTORS))
    mean2 = pos2["Speed"].groupby(s2.values).mean().reindex(range(MINI_SECTORS))
    # a part with no samples for one driver goes to the other
    sectors = tuple(0 if (m1 if pd.notna(m1) else -1) >= (m2 if pd.notna(m2) else -1) else 1
                    for m1, m2 in zip(mean1, mean2))
    first, missing_a = style.colour(drivers[0][1])
    second, _ = style.colour(drivers[1][1])
    second = style.clash(first, second)
    return DominanceData(title, tuple(pos1["X"]), tuple(pos1["Y"]), tuple(sectors[s] for s in s1), sectors,
                         ((drivers[0][0], first), (drivers[1][0], second)), rotation)


def _code(driver):
    return driver.get("code") or driver["familyName"][:3].upper()


def is_dnf(status: str) -> bool:
    status = (status or "").strip()
    return not (status in ("Finished", "Lapped") or re.fullmatch(r"\+\d+ Laps?", status))


def is_mechanical_dnf(status: str) -> bool:
    return is_dnf(status) and (status or "").strip().lower() not in DRIVER_CAUSED


def compute_avgpos(races, key, category, exclude) -> tuple[list, int]:
    """[(label, average, constructorId)] best first, and the season's largest grid.

    `key` is "Results" or "QualifyingResults"; `exclude` is "none", "mechanical" or "all" (races only)."""
    totals, grid = {}, 0
    for race in races:
        grid = max(grid, len(race[key]))
        for r in race[key]:
            status = r.get("status", "Finished")
            if key == "Results" and ((exclude == "all" and is_dnf(status))
                                     or (exclude == "mechanical" and is_mechanical_dnf(status))):
                continue
            if not str(r.get("position", "")).isdigit():
                continue
            team = r["Constructor"]
            ident, label = ((team["constructorId"], team["name"]) if category == "Teams"
                            else (r["Driver"]["driverId"], _code(r["Driver"])))
            entry = totals.setdefault(ident, {"label": label, "sum": 0, "n": 0, "team": team["constructorId"]})
            entry["sum"] += int(r["position"])
            entry["n"] += 1
            entry["team"] = team["constructorId"]   # most recent team
    rows = [(e["label"], e["sum"] / e["n"], e["team"]) for e in totals.values() if e["n"]]
    return sorted(rows, key=lambda r: r[1]), grid


def compute_h2h(races, key, exclude_dnfs, team_order=()) -> list:
    """[(constructorId, team name, left code, left wins, right code, right wins)] per teammate pairing.

    A pairing exists for every two drivers who shared at least one round in the same team."""
    tally, names = {}, {}
    for race in races:
        teams = {}
        for r in race[key]:
            if not str(r.get("position", "")).isdigit():
                continue
            names[r["Constructor"]["constructorId"]] = r["Constructor"]["name"]
            teams.setdefault(r["Constructor"]["constructorId"], []).append(
                (_code(r["Driver"]), int(r["position"]), key == "Results" and is_dnf(r.get("status", "Finished"))))
        for team, entries in teams.items():
            for a, b in itertools.combinations(sorted(entries), 2):
                pair = tally.setdefault((team, a[0], b[0]), [0, 0])   # created even when the round is skipped
                if exclude_dnfs and (a[2] or b[2]):
                    continue
                pair[0 if a[1] < b[1] else 1] += 1
    order = {team: i for i, team in enumerate(team_order)}
    out = []
    for (team, a, b), (wins_a, wins_b) in sorted(tally.items(), key=lambda kv: (order.get(kv[0][0], 99), kv[0])):
        left, right = ((a, wins_a), (b, wins_b)) if wins_a >= wins_b else ((b, wins_b), (a, wins_a))
        out.append((team, names[team], *left, *right))
    return out


# ------------------------------------------------------------------- cache

async def cached(key: tuple, build):
    """Serve (png, meta) for `key` from disk, or build and store it. A finished session's plot never changes."""
    digest = hashlib.sha1(repr(key).encode()).hexdigest()
    path = ctx.config.data_dir / "plots" / f"{digest}.png"
    meta = await ctx.db.cache_get(f"plot:{digest}")
    if meta is not None and path.exists():
        return path.read_bytes(), meta
    png, meta = await build()
    path.write_bytes(png)
    await ctx.db.cache_set(f"plot:{digest}", meta)
    return png, meta


# --------------------------------------------------------- shared plumbing

async def _session(year, round, min_year, kind):
    """(year, event, session with results loaded)."""
    year, event = await params.resolve(year, round, min_year, kind)
    return year, event, await fastf1_src.load(year, event.round, _fastf1_name(event, kind))


def _fastf1_name(event, kind):
    return event.session(kind).name


def _driver(session, text, year, event, kind) -> str:
    try:
        return params.find_driver(session.results, text)
    except UserError:
        raise UserError(f"{str(text).upper()} didn't take part in {year} {event.name} {kind}.") from None


async def _laps(year, event, kind, telemetry=False):
    session = await fastf1_src.load(year, event.round, _fastf1_name(event, kind), laps=True, telemetry=telemetry)
    try:
        laps = session.laps
    except Exception:
        laps = None
    if laps is None or len(laps) == 0:
        raise UserError(f"No lap data is available for {year} {event.name} {kind}.")
    return session, laps


def _colours(session, codes):
    return {code: fastf1_src.driver_color(code, session) for code in codes}


def _two_drivers(session, driver1, driver2, year, event, kind):
    a, b = (_driver(session, d, year, event, kind) for d in (driver1, driver2))
    if a == b:
        raise UserError("Use 2 different drivers!")
    return a, b


async def _render(module_function, data):
    return await asyncio.to_thread(module_function, data)


# ---------------------------------------------------------------- commands

async def laptimes(driver1, driver2, round, year):
    from ..render.plots import race
    year, event, session = await _session(year, round, 2018, "Race")
    a, b = _two_drivers(session, driver1, driver2, year, event, "Race")

    async def build():
        full, laps = await _laps(year, event, "Race")
        data = compute_laptimes(laps, (a, b), _colours(full, (a, b)), f"{year} {event.name} {a} vs {b}")
        return await _render(race.laptimes, data), {
            "title": "Lap Times", "description": f"{year} {event.name}\n{a} vs {b}"}
    return await cached(("laptimes", year, event.round, *sorted((a, b))), build)


async def positions(round, year):
    from ..render.plots import race
    year, event, session = await _session(year, round, 2018, "Race")

    async def build():
        full, laps = await _laps(year, event, "Race")
        codes = list(full.results["Abbreviation"])
        data = compute_positions(laps, full.results, _colours(full, codes),
                                 f"Position Changes During {year} {event.name}")
        return await _render(race.positions, data), {
            "title": "Driver Positions", "description": f"{year} {event.name}"}
    return await cached(("positions", year, event.round), build)


async def strategy(round, year):
    from ..render.plots import race
    year, event, session = await _session(year, round, 2018, "Race")

    async def build():
        full, laps = await _laps(year, event, "Race")
        data = compute_strategy(laps, full.results, year, f"{event.name}\nTire Strategy")
        return await _render(race.strategy, data), {
            "title": f"{event.name} Tire Strategy", "footer": "2018 tire colors used" if year == 2018 else None}
    return await cached(("strategy", year, event.round), build)


async def qualigap(round, year):
    from ..render.plots import race
    year, event, session = await _session(year, round, 2018, "Qualifying")

    async def build():
        codes = list(session.results["Abbreviation"])
        data = compute_qualigap(session.results, _colours(session, codes),
                                f"{year} {event.name}\nQualifying Gap to Pole")
        return await _render(race.qualigap, data), {
            "title": "Qualifying Gap to Leader", "description": f"{year} {event.name}"}
    return await cached(("qualigap", year, event.round), build)


async def consistency(driver, round, year):
    from ..render.plots import race
    year, event, session = await _session(year, round, 2018, "Race")
    code = _driver(session, driver, year, event, "Race")

    async def build():
        full, laps = await _laps(year, event, "Race")
        data = compute_consistency(laps[laps["Driver"] == code], code,
                                   f"{code} Laptime Consistency\n{year} {event.name}")
        return await _render(race.consistency, data), {
            "title": f"{code} Laptime Consistency",
            "description": f"{year} {event.name}\nσ = {data.std:.3f} s",
            "footer": "Standard deviation (σ) & mean calculated excluding outliers"}
    return await cached(("consistency", year, event.round, code), build)


def _pick_lap(laps, code, lap_number):
    d = laps[(laps["Driver"] == code) & laps["LapTime"].notna()]
    if lap_number is not None:
        d = d[d["LapNumber"] == lap_number]
        if d.empty:
            raise UserError(f"{code} has no lap {lap_number} in this session.")
        return d.iloc[0]
    if d.empty:
        raise UserError(f"{code} set no timed lap in this session.")
    return d.loc[d["LapTime"].idxmin()]


async def telemetry(driver1, driver2, round, session_name, year, lap):
    from ..render.plots import telemetry as plot
    kind = session_name or "Race"
    year, event, session = await _session(year, round, 2018, kind)
    codes = [_driver(session, driver1, year, event, kind)]
    if driver2:
        codes = list(_two_drivers(session, driver1, driver2, year, event, kind))
    which = f"Lap {lap}" if lap is not None else "Fastest Lap"

    async def build():
        full, laps = await _laps(year, event, kind, telemetry=True)
        colours = _colours(full, codes)
        first, missing = style.colour(colours.get(codes[0]))
        palette = [first] + ([style.clash(first, style.colour(colours.get(codes[1]))[0])] if len(codes) > 1 else [])
        traces, lines = [], [f"{year} {event.name}"]
        for code, colour in zip(codes, palette):
            row = _pick_lap(laps, code, lap)
            car = await asyncio.to_thread(fastf1_src.car_data, row)
            seconds = row["LapTime"].total_seconds()
            traces.append(Trace(code, colour, tuple(car["Distance"]), tuple(car["Speed"]), tuple(car["Throttle"]),
                                tuple(car["Brake"].astype(float)), seconds))
            lines.append(f"{code}: {util.fmt_lap(seconds)}")
        circuit = fastf1_src.circuit_info(full)
        corners = () if circuit is None else tuple(
            (float(c["Distance"]), f"{int(c['Number'])}{c['Letter'] or ''}") for _, c in circuit.corners.iterrows())
        data = TelemetryData(f"{which} Telemetry", tuple(traces), corners, missing)
        return await _render(plot.telemetry, data), {
            "title": f"{which} {kind} Telemetry", "description": "\n".join(lines)}
    return await cached(("telemetry", year, event.round, kind, lap, *sorted(codes)), build)


async def trackdominance(driver1, driver2, round, session_name, year):
    from ..render.plots import telemetry as plot
    kind = session_name or "Qualifying"
    year, event, session = await _session(year, round, 2018, kind)
    a, b = sorted(_two_drivers(session, driver1, driver2, year, event, kind))

    async def build():
        full, laps = await _laps(year, event, kind, telemetry=True)
        colours = _colours(full, (a, b))
        pos = [await asyncio.to_thread(fastf1_src.position_data, _pick_lap(laps, code, None)) for code in (a, b)]
        circuit = fastf1_src.circuit_info(full)
        data = compute_dominance(pos[0], pos[1], ((a, colours.get(a)), (b, colours.get(b))),
                                 f"{a} vs {b}\n{year} {event.name} {kind}\nTrack Dominance on Fastest Lap",
                                 float(circuit.rotation) if circuit is not None else 0.0)
        return await _render(plot.dominance, data), {
            "title": f"Track Dominance During {kind}", "description": f"{year} {event.name}\n{a} vs {b}"}
    return await cached(("trackdominance", year, event.round, kind, a, b), build)


async def _season(year, session_name, min_year):
    """(year, races, key) from Jolpica for a season-wide plot."""
    qualifying = session_name == "Qualifying"
    year = await params.resolve_year(year, 1994 if qualifying else min_year, session_name)
    races = await (jolpica.season_qualifying(year) if qualifying else jolpica.season_results(year))
    if not races:
        raise UserError(f"No {session_name.lower()} results are available for {year}.")
    return year, races, "QualifyingResults" if qualifying else "Results"


async def _team_colours(year, races, key):
    """constructorId -> colour or None. FastF1 only knows team colours from 2018."""
    teams = {r["Constructor"]["constructorId"]: r["Constructor"]["name"] for race in races for r in race[key]}
    if year < 2018:
        return dict.fromkeys(teams)
    try:
        session = await asyncio.to_thread(fastf1_src.fastf1.get_session, year, int(races[-1]["round"]), "R")
        return {cid: await asyncio.to_thread(fastf1_src.team_color, name, session) for cid, name in teams.items()}
    except Exception as e:
        log.warning("team colours unavailable for %s: %s", year, e)
        return dict.fromkeys(teams)


EXCLUDE_TEXT = {
    "none": (" (DNFs Included)", "DNFs included in calculation"),
    "mechanical": (" (Mechanical DNFs Excluded)", "Mechanical DNFs excluded from calculation"),
    "all": (" (DNF/DNS Excluded)", "DNF/DNS excluded from calculation"),
}


async def avgpos(category, session_name, exclude, year):
    from ..render.plots import season
    year, races, key = await _season(year, session_name, 1950)
    if key == "QualifyingResults":
        exclude = "none"   # no effect on qualifying

    async def build():
        rows, grid = compute_avgpos(races, key, category, exclude)
        if not rows:
            raise UserError(f"No {session_name.lower()} results are available for {year}.")
        colours = await _team_colours(year, races, key)
        styled = [(label, value, *style.colour(colours.get(team))) for label, value, team in rows]
        name = f"Average {category} {session_name} Finish Position {year}"
        suffix, description = EXCLUDE_TEXT[exclude] if key == "Results" else ("", "Qualifying classification")
        data = BarsData(name + suffix, tuple(r[:3] for r in styled), grid, category == "Drivers",
                        any(r[3] for r in styled))
        return await _render(season.avgpos, data), {"title": name, "description": description}
    return await cached(("avgpos", year, len(races), category, session_name, exclude), build)


async def h2h(session_name, exclude_dnfs, year):
    from ..render.plots import season
    year, races, key = await _season(year, session_name, 1950)
    exclude_dnfs = bool(exclude_dnfs) and key == "Results"

    async def build():
        try:
            order = [r["Constructor"]["constructorId"] for r in (await jolpica.constructor_standings(year))["rows"]]
        except SourceError:
            order = []
        pairs = compute_h2h(races, key, exclude_dnfs, order)
        if not pairs:
            raise UserError(f"No teammate pairings were found for {year}.")
        colours = await _team_colours(year, races, key)
        styled = [(team, name, *style.colour(colours.get(team)), *rest) for team, name, *rest in pairs]
        retirements = "Excluded" if exclude_dnfs else "Included"
        data = H2HData(f"{year} {session_name} Head to Head (Retirements {retirements})",
                       tuple((t, n, c, *rest) for t, n, c, _, *rest in styled), any(r[3] for r in styled))
        return await _render(season.h2h, data), {
            "title": f"{year} {session_name} Head to Head",
            "footer": "All retirements excluded" if exclude_dnfs else "Retirements included"}
    return await cached(("h2h", year, len(races), session_name, exclude_dnfs), build)


async def circuit_image(event) -> bool:
    """Draw and store the circuit outline for an event from an earlier season's qualifying. True if it exists."""
    from ..render.plots import telemetry as plot
    circuit = await info.circuit_of(event)
    if circuit is None:
        return False
    path = info.circuit_path(circuit["circuitId"])
    if path.exists():
        return True
    for year in range(event.year - 1, max(event.year - 4, 2017), -1):
        try:
            previous = next((r for r in await jolpica.races(year)
                             if r["Circuit"]["circuitId"] == circuit["circuitId"]), None)
            if previous is None:
                continue
            session = await fastf1_src.load(year, int(previous["round"]), "Qualifying", laps=True, telemetry=True)
            laps = session.laps[session.laps["LapTime"].notna()]
            pos = await asyncio.to_thread(fastf1_src.position_data, laps.loc[laps["LapTime"].idxmin()])
            info_ = fastf1_src.circuit_info(session)
            data = CircuitData(tuple(pos["X"]), tuple(pos["Y"]), float(info_.rotation) if info_ is not None else 0.0)
            path.write_bytes(await _render(plot.circuit, data))
            return True
        except Exception as e:
            log.warning("circuit image for %s from %s failed: %s", circuit["circuitId"], year, e)
    return False
