"""Shared parameter rules: year, round, driver, session (spec 00)."""
from .. import util
from ..errors import SourceError, UserError
from ..series import Event, f1
from ..sources import jolpica

SESSION_CHOICES = ["Practice 1", "Practice 2", "Practice 3", "Sprint Qualifying", "Sprint", "Qualifying", "Race"]


async def season(year: int) -> list[Event]:
    return await f1.season_schedule(year)


def completed(events: list[Event], kind: str, now=None) -> list[Event]:
    """Events whose `kind` session has finished, in round order."""
    now = now or util.now()
    return [e for e in events if e.session(kind) and e.session(kind).end_utc <= now]


async def resolve_year(year: int | None, min_year: int, kind: str = "Race") -> int:
    """The given year if valid; otherwise the season of the latest completed `kind` session."""
    this_year = util.now().year
    if year is not None:
        if not min_year <= year <= this_year:
            raise UserError(f"Year must be between {min_year} and {this_year}.")
        return year
    if completed(await season(this_year), kind):
        return this_year
    return this_year - 1


def find_round(events: list[Event], text: str) -> Event | None:
    text = str(text).strip()
    if text.isdigit():
        return next((e for e in events if e.round == int(text)), None)
    needle = util.fold(text)
    if not needle:
        return None
    return next((e for e in events
                 if needle in util.fold(e.name) or needle in util.fold(e.country)
                 or needle in util.fold(e.location)), None)


async def resolve_event(year: int, round: str | None, kind: str = "Race") -> Event:
    """The requested event, or the latest one whose `kind` session is complete."""
    events = await season(year)
    label = kind.lower()
    if round is None or not str(round).strip():
        done = completed(events, kind)
        if not done:
            raise UserError(f"No {label} has been run yet in {year}.")
        return done[-1]
    event = find_round(events, round)
    if event is None:
        raise UserError(f'Round "{round}" not found for {year}.')
    slot = event.session(kind)
    if slot is None:
        available = ", ".join(s.name for s in event.sessions)
        raise UserError(f"{event.name} has no {kind} session. It has: {available}.")
    if slot.start_utc > util.now():
        raise UserError(f"That {label} hasn't happened yet.")
    return event


async def resolve(year, round, min_year, kind="Race") -> tuple[int, Event]:
    year = await resolve_year(year, min_year, kind)
    return year, await resolve_event(year, round, kind)


def find_driver(results, text: str) -> str:
    """Driver code from free text, matched against a session's results frame."""
    needle = util.fold(text)
    for _, row in results.iterrows():
        names = (row.get("Abbreviation"), row.get("LastName"), row.get("FullName"), row.get("DriverId"))
        if needle and needle in {util.fold(n) for n in names if isinstance(n, str)}:
            return row["Abbreviation"]
    raise UserError(f'Driver "{text}" wasn\'t found in that session.')


# --- autocomplete helpers (never raise: autocomplete must fail quietly) ---

async def round_choices(year: int | None, current: str) -> list[tuple[str, str]]:
    try:
        events = await season(year or util.now().year)
    except SourceError:
        return []
    needle = util.fold(current)
    return [(f"{e.round}. {e.name}", str(e.round)) for e in events
            if needle in util.fold(f"{e.round}. {e.name} {e.country} {e.location}")][:25]


async def driver_choices(year: int | None, current: str) -> list[tuple[str, str]]:
    try:
        drivers = await jolpica.season_drivers(year or util.now().year)
    except SourceError:
        return []
    needle = util.fold(current)
    out = []
    for d in drivers:
        code = d.get("code") or d["familyName"][:3].upper()
        label = f"{code} — {d['givenName']} {d['familyName']}"
        if needle in util.fold(label):
            out.append((label, code))
    return out[:25]
