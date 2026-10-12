"""Series providers. Only the schedule is series-dependent, so the interface is small."""
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Protocol


@dataclass(frozen=True)
class SessionSlot:
    name: str              # as the series names it: "Practice 1", "Sprint Qualifying", "Race"
    start_utc: datetime    # timezone-aware

    @property
    def end_utc(self) -> datetime:
        """Nominal end: when results can reasonably be expected."""
        return self.start_utc + timedelta(hours=2 if self.name == "Race" else 1)


@dataclass(frozen=True)
class Event:
    series: str
    year: int
    round: int
    name: str              # "Singapore Grand Prix"
    country: str
    location: str
    sessions: tuple[SessionSlot, ...]   # chronological

    def session(self, name: str) -> SessionSlot | None:
        # 2023 called sprint qualifying the "Sprint Shootout"
        names = ("Sprint Qualifying", "Sprint Shootout") if name == "Sprint Qualifying" else (name,)
        return next((s for s in self.sessions if s.name in names), None)

    @property
    def race(self) -> SessionSlot | None:
        return self.session("Race")

    @property
    def qualifying(self) -> SessionSlot | None:
        return self.session("Qualifying")


class Series(Protocol):
    key: str
    name: str

    async def season_schedule(self, year: int) -> list[Event]: ...


def get(key: str = "f1") -> Series:
    from . import f1
    return {"f1": f1}[key]
