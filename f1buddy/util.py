import json
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

ASSETS = Path(__file__).parent / "assets"
_COUNTRIES = json.loads((ASSETS / "countries.json").read_text())
_NATIONALITIES = json.loads((ASSETS / "nationalities.json").read_text())


def now() -> datetime:
    """Current UTC time. Tests replace this to fix the clock."""
    return datetime.now(timezone.utc)


def ts(dt: datetime, style: str = "f") -> str:
    """Discord timestamp, rendered in each viewer's local time."""
    return f"<t:{int(dt.timestamp())}:{style}>"


def fold(text: str) -> str:
    """Lower-case and strip accents, for forgiving comparisons."""
    text = unicodedata.normalize("NFKD", str(text))
    return "".join(c for c in text if not unicodedata.combining(c)).casefold().strip()


def _flag(code):
    return "".join(chr(0x1F1E6 + ord(c) - ord("a")) for c in code) if code else ""


def country_flag(name) -> str:
    return _flag(_COUNTRIES.get(fold(name or "")))


def nationality_flag(name) -> str:
    return _flag(_NATIONALITIES.get(fold(name or "")))


def fmt_points(value) -> str:
    value = float(value)
    return str(int(value)) if value == int(value) else f"{value:g}"


def fmt_lap(seconds) -> str:
    """Seconds -> M:SS.mmm"""
    millis = round(float(seconds) * 1000)
    return f"{millis // 60000}:{millis % 60000 // 1000:02d}.{millis % 1000:03d}"


def clamp(text: str, limit: int) -> str:
    text = text or ""
    return text if len(text) <= limit else text[: limit - 1] + "…"
