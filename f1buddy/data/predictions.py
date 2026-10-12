"""Predictions game (spec 06): scoring, locks, storage. No Discord types here."""
import time
from datetime import timedelta

from .. import ctx, util
from ..errors import SourceError, UserError
from ..series import Event
from ..sources import fastf1_src, jolpica
from . import params

POLE_POINTS = 5
EXACT_POINTS = 5        # podium driver in the exact position
MISPLACED_POINTS = 2    # podium driver predicted, but in a different podium position
PERFECT_BONUS = 5       # all three podium positions exact
SERIES = "f1"


def score(prediction, pole: str | None, podium: tuple) -> tuple[int, int]:
    """(points, exact podium hits) for one prediction. Either part of the prediction may be missing."""
    points = exact = 0
    if prediction["pole"] and prediction["pole"] == pole:
        points += POLE_POINTS
    picks = (prediction["p1"], prediction["p2"], prediction["p3"])
    if all(picks):
        for pick, actual in zip(picks, podium):
            if pick == actual:
                points += EXACT_POINTS
                exact += 1
            elif pick in podium:
                points += MISPLACED_POINTS
        if exact == 3:
            points += PERFECT_BONUS
    return points, exact


def lock_time(event: Event, part: str):
    slot = event.qualifying if part == "pole" else event.race
    return slot.start_utc if slot else None


async def _events(now):
    events = await params.season(now.year)
    try:
        events = events + await params.season(now.year + 1)
    except SourceError:
        pass
    return [e for e in events if e.race and e.qualifying]


async def open_event(part: str, now=None) -> Event:
    """The next race whose `part` ('pole' or 'podium') hasn't locked."""
    now = now or util.now()
    event = next((e for e in await _events(now) if lock_time(e, part) > now), None)
    if event is None:
        raise UserError("There's no upcoming race to predict yet.")
    return event


async def current_event(now=None) -> Event:
    """What /predictions shows by default: a weekend in progress or awaiting its score, else the next race."""
    now = now or util.now()
    events = await _events(now)
    recent = [e for e in events if now - timedelta(days=3) <= e.race.start_utc <= now]
    if recent and not await is_scored(recent[-1]):
        return recent[-1]
    upcoming = next((e for e in events if e.race.start_utc > now), None)
    if upcoming is None:
        if not events:
            raise UserError("There's no race to show predictions for.")
        return events[-1]
    return upcoming


async def season_driver(year: int, text: str) -> str:
    """Driver code for free text, limited to drivers entered this season."""
    needle = util.fold(text)
    for d in await jolpica.season_drivers(year):
        code = d.get("code") or d["familyName"][:3].upper()
        names = {util.fold(code), util.fold(d["familyName"]), util.fold(f"{d['givenName']} {d['familyName']}"),
                 util.fold(d["driverId"])}
        if needle in names:
            return code
    raise UserError(f'Driver "{text}" isn\'t entered in the {year} season.')


async def get(guild_id, user_id, event: Event):
    return await ctx.db.one("SELECT * FROM predictions WHERE guild_id=? AND user_id=? AND series=? AND year=? "
                            "AND round=?", guild_id, user_id, SERIES, event.year, event.round)


async def save_pole(guild_id, user_id, driver: str, now=None):
    now = now or util.now()
    event = await open_event("pole", now)
    podium_event = await open_event("podium", now)
    if podium_event.round != event.round or podium_event.year != event.year:
        # qualifying for the current weekend has started; pole now belongs to the following race
        raise UserError(f"Pole predictions for {podium_event.name} are locked. "
                        "You can still predict the podium until the race starts.")
    code = await season_driver(event.year, driver)
    await ctx.db.q(
        "INSERT INTO predictions (guild_id, user_id, series, year, round, pole, updated_at) VALUES (?,?,?,?,?,?,?) "
        "ON CONFLICT (guild_id, user_id, series, year, round) DO UPDATE SET pole=excluded.pole, "
        "updated_at=excluded.updated_at", guild_id, user_id, SERIES, event.year, event.round, code, int(time.time()))
    return event, await get(guild_id, user_id, event)


async def save_podium(guild_id, user_id, p1: str, p2: str, p3: str, now=None):
    now = now or util.now()
    event = await open_event("podium", now)
    codes = [await season_driver(event.year, d) for d in (p1, p2, p3)]
    if len(set(codes)) != 3:
        raise UserError("Pick three different drivers for the podium.")
    await ctx.db.q(
        "INSERT INTO predictions (guild_id, user_id, series, year, round, p1, p2, p3, updated_at) "
        "VALUES (?,?,?,?,?,?,?,?,?) ON CONFLICT (guild_id, user_id, series, year, round) DO UPDATE SET "
        "p1=excluded.p1, p2=excluded.p2, p3=excluded.p3, updated_at=excluded.updated_at",
        guild_id, user_id, SERIES, event.year, event.round, *codes, int(time.time()))
    return event, await get(guild_id, user_id, event)


async def for_event(guild_id, event: Event):
    """Predictions for one server and race, each with its score (None until scored)."""
    return await ctx.db.q(
        "SELECT p.*, s.points, s.exact_hits FROM predictions p LEFT JOIN prediction_scores s "
        "ON s.guild_id=p.guild_id AND s.user_id=p.user_id AND s.series=p.series AND s.year=p.year "
        "AND s.round=p.round WHERE p.guild_id=? AND p.series=? AND p.year=? AND p.round=? "
        "ORDER BY COALESCE(s.points, -1) DESC, p.updated_at", guild_id, SERIES, event.year, event.round)


def _result_key(event):
    return f"pred:result:{event.year}:{event.round}"


async def is_scored(event: Event) -> bool:
    return await ctx.db.cache_get(_result_key(event)) is not None


async def actual(event: Event):
    """{'pole': code, 'podium': [codes]} once the race has been scored, else None."""
    return await ctx.db.cache_get(_result_key(event))


async def official_result(event: Event) -> tuple[str, tuple]:
    """(pole-sitter, podium) from the official classification. Pole is fastest in qualifying."""
    quali = await fastf1_src.load(event.year, event.round, "Qualifying", fresh=True)
    race = await fastf1_src.load(event.year, event.round, "Race", fresh=True)
    try:
        pole = quali.results.sort_values("Position")["Abbreviation"].iloc[0]
        podium = tuple(race.results.sort_values("Position")["Abbreviation"].iloc[:3])
    except Exception as e:
        raise SourceError("FastF1", f"no classification for {event.year} round {event.round}: {e}") from e
    if len(podium) < 3:
        raise SourceError("FastF1", "classification has fewer than three finishers")
    return pole, podium


async def score_round(event: Event, pole: str, podium: tuple) -> dict:
    """Score every prediction for a race. Idempotent. Returns {guild_id: number of scores that changed}."""
    changed = {}
    rows = await ctx.db.q(
        "SELECT p.*, s.points AS old FROM predictions p LEFT JOIN prediction_scores s "
        "ON s.guild_id=p.guild_id AND s.user_id=p.user_id AND s.series=p.series AND s.year=p.year "
        "AND s.round=p.round WHERE p.series=? AND p.year=? AND p.round=?", SERIES, event.year, event.round)
    for row in rows:
        points, exact = score(row, pole, podium)
        changed.setdefault(row["guild_id"], 0)
        if row["old"] != points:
            changed[row["guild_id"]] += 1
        await ctx.db.q("INSERT OR REPLACE INTO prediction_scores VALUES (?,?,?,?,?,?,?)", row["guild_id"],
                       row["user_id"], SERIES, event.year, event.round, points, exact)
    await ctx.db.cache_set(_result_key(event), {"pole": pole, "podium": list(podium)})
    return changed


async def leaderboard(guild_id, year: int):
    """[(rank, user_id, points, races, exact hits)] best first; ties share a rank."""
    rows = await ctx.db.q(
        "SELECT user_id, SUM(points) AS points, COUNT(*) AS races, SUM(exact_hits) AS exact "
        "FROM prediction_scores WHERE guild_id=? AND series=? AND year=? GROUP BY user_id "
        "ORDER BY points DESC, exact DESC, user_id", guild_id, SERIES, year)
    return [(1 + sum(1 for other in rows if other["points"] > r["points"]),
             r["user_id"], r["points"], r["races"], r["exact"]) for r in rows]
