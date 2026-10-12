from datetime import timezone

import pandas as pd

from ..sources import fastf1_src
from . import Event, SessionSlot

key = "f1"
name = "Formula 1"


def events_from_frame(df, year: int) -> list[Event]:
    events = []
    for _, row in df.iterrows():
        if int(row["RoundNumber"]) < 1:
            continue
        slots = []
        for i in range(1, 6):
            session_name = row.get(f"Session{i}")
            if not isinstance(session_name, str) or not session_name or session_name == "None":
                continue
            start = row.get(f"Session{i}DateUtc")
            if pd.isna(start):  # old seasons have no session times; the event date is close enough
                start = row["EventDate"]
            if pd.isna(start):
                continue
            slots.append(SessionSlot(session_name, pd.Timestamp(start).to_pydatetime().replace(tzinfo=timezone.utc)))
        slots.sort(key=lambda s: s.start_utc)
        events.append(Event(key, year, int(row["RoundNumber"]), str(row["EventName"]),
                            str(row["Country"]), str(row["Location"]), tuple(slots)))
    return events


async def season_schedule(year: int) -> list[Event]:
    return events_from_frame(await fastf1_src.schedule(year), year)
