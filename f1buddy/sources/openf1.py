"""OpenF1, free tier: data for finished sessions (2023 onwards). Used for the /live recap."""
from . import http

BASE = "https://api.openf1.org/v1"


async def _get(endpoint, **params):
    return await http.get_json("OpenF1", f"{BASE}/{endpoint}", params)


async def latest_session() -> dict | None:
    sessions = await _get("sessions", session_key="latest")
    return sessions[0] if sessions else None


async def recap(session_key) -> dict:
    """Raw result, weather, race control and driver lists for one finished session."""
    return {
        "result": await _get("session_result", session_key=session_key),
        "weather": await _get("weather", session_key=session_key),
        "race_control": await _get("race_control", session_key=session_key),
        "drivers": await _get("drivers", session_key=session_key),
    }
