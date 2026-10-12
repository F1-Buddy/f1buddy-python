"""FastF1 access. Everything here is blocking; callers use the async wrappers."""
import asyncio
import logging
import threading
import time
from collections import OrderedDict

import fastf1
import fastf1.plotting

from ..errors import SourceError, UserError

log = logging.getLogger(__name__)
_schedules = {}             # year -> (fetched_at, DataFrame)
_sessions = OrderedDict()   # (year, round, name) -> (flags, Session); small LRU
_locks = {}
_guard = threading.Lock()
FLAGS = ("laps", "telemetry", "weather", "messages")


def init(data_dir):
    cache = data_dir / "fastf1"
    cache.mkdir(parents=True, exist_ok=True)
    fastf1.Cache.enable_cache(str(cache))
    fastf1.set_log_level("WARNING")


def schedule_sync(year):
    hit = _schedules.get(year)
    if hit and time.monotonic() - hit[0] < 6 * 3600:
        return hit[1]
    try:
        df = fastf1.get_event_schedule(year, include_testing=False)
    except Exception as e:
        raise SourceError("FastF1", f"schedule {year}: {e}") from e
    _schedules[year] = (time.monotonic(), df)
    return df


def load_sync(year, round, name, fresh=False, **flags):
    """A loaded session. Concurrent calls for the same session share one download.

    `fresh` skips the in-memory copy, for results that may have been incomplete last time."""
    key = (year, round, name)
    want = {f: bool(flags.get(f)) for f in FLAGS}
    with _guard:
        lock = _locks.setdefault(key, threading.Lock())
    with lock:
        hit = None if fresh else _sessions.get(key)
        if hit and all(hit[0][f] or not want[f] for f in FLAGS):
            _sessions.move_to_end(key)
            return hit[1]
        if hit:  # reload with the union of what was and is wanted
            want = {f: want[f] or hit[0][f] for f in FLAGS}
        try:
            session = fastf1.get_session(year, round, name)
        except ValueError as e:
            raise UserError(f"{name} isn't part of that event.") from e
        except Exception as e:
            raise SourceError("FastF1", f"get_session {key}: {e}") from e
        try:
            session.load(**want)
        except Exception as e:
            raise SourceError("FastF1", f"load {key}: {e}") from e
        _sessions[key] = (want, session)
        while len(_sessions) > 6:
            _sessions.popitem(last=False)
        return session


async def schedule(year):
    return await asyncio.to_thread(schedule_sync, year)


async def load(year, round, name, **flags):
    return await asyncio.to_thread(load_sync, year, round, name, **flags)


# --- helpers that need real FastF1 objects; data functions get plain frames ---

def driver_color(code, session):
    try:
        return fastf1.plotting.get_driver_color(code, session)
    except Exception:
        return None


def team_color(team, session):
    try:
        return fastf1.plotting.get_team_color(team, session)
    except Exception:
        return None


def car_data(lap):
    """Speed/Throttle/Brake against Distance for one lap."""
    return lap.get_car_data().add_distance()


def position_data(lap):
    """X/Y/Speed against Distance for one lap."""
    return lap.get_telemetry()


def circuit_info(session):
    try:
        return session.get_circuit_info()
    except Exception:
        return None
