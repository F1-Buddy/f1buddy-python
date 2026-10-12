from dataclasses import dataclass
from datetime import date

from .. import ctx
from . import http


@dataclass(frozen=True)
class DayForecast:
    day: date
    temp_min: float
    temp_max: float
    precipitation_mm: float
    precipitation_probability: int | None


async def forecast(lat, lon, start: date, end: date, cache_key: str) -> list[DayForecast]:
    """Daily forecast from Open-Meteo for the given dates. Raises SourceError."""
    key = f"weather:{cache_key}"
    daily = await ctx.db.cache_get(key)
    if daily is None:
        data = await http.get_json("Open-Meteo", "https://api.open-meteo.com/v1/forecast", {
            "latitude": lat, "longitude": lon, "timezone": "auto",
            "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum,precipitation_probability_max",
            "start_date": start.isoformat(), "end_date": end.isoformat(),
        })
        daily = data["daily"]
        await ctx.db.cache_set(key, daily, 3600)
    return [
        DayForecast(date.fromisoformat(d), lo, hi, rain or 0.0, prob)
        for d, lo, hi, rain, prob in zip(
            daily["time"], daily["temperature_2m_min"], daily["temperature_2m_max"],
            daily["precipitation_sum"], daily["precipitation_probability_max"])
        if lo is not None and hi is not None
    ]
