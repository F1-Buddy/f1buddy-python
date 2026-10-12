"""FIA decision documents. The only HTML scraper in the bot.

`parse_listing` is the single place that knows what the page looks like. It keys on the PDF links
themselves, not on CSS classes or layout, so cosmetic changes to fia.com don't break it.
"""
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from urllib.parse import unquote, urljoin
from zoneinfo import ZoneInfo

from bs4 import BeautifulSoup

from ..errors import ParseError
from . import http

BASE = "https://www.fia.com"
LISTING_URL = f"{BASE}/documents/championships/fia-formula-one-world-championship-14"
_PUBLISHED = re.compile(r"Published on\s+(\d{2}\.\d{2}\.\d{2})\s+(\d{2}:\d{2})")
_PARIS = ZoneInfo("Europe/Paris")   # the page labels its times "CET"


@dataclass(frozen=True)
class FiaDocument:
    url: str                        # absolute PDF URL; the document's identity
    title: str                      # "Doc 91 - Championship Points"
    event: str | None               # "Singapore Grand Prix"
    published_at: datetime | None   # UTC


def _event_from_filename(name: str) -> str | None:
    # 2026_singapore_grand_prix_-_championship_points.pdf
    if "_-_" not in name:
        return None
    words = [w for w in name.split("_-_")[0].split("_") if w and not w.isdigit()]
    return " ".join(w.capitalize() for w in words) or None


def _event_from_page(link) -> str | None:
    heading = link.find_previous(
        lambda tag: tag.name in ("h1", "h2", "h3", "h4", "h5", "h6")
        or any("event" in c for c in tag.get("class", [])))
    text = heading.get_text(" ", strip=True) if heading else ""
    return text if 0 < len(text) <= 80 else None


def parse_listing(html: str) -> list[FiaDocument]:
    """Documents on the listing page, newest first. Raises ParseError if there are none."""
    soup = BeautifulSoup(html, "html.parser")
    docs, seen = [], set()
    for link in soup.find_all("a", href=True):
        href = link["href"].strip()
        if not href.lower().endswith(".pdf") or "decision-document" not in href:
            continue
        url = urljoin(BASE, href)
        if url in seen:
            continue
        seen.add(url)
        filename = unquote(url.rsplit("/", 1)[1])

        text = " ".join(link.get_text(" ", strip=True).split())
        match = _PUBLISHED.search(text) or _PUBLISHED.search(
            " ".join(link.parent.get_text(" ", strip=True).split()) if link.parent else "")
        published = None
        if match:
            local = datetime.strptime(" ".join(match.groups()), "%d.%m.%y %H:%M").replace(tzinfo=_PARIS)
            published = local.astimezone(timezone.utc)
        title = text.split("Published on")[0].strip() or filename[:-4].replace("_", " ")

        docs.append(FiaDocument(url, title, _event_from_filename(filename) or _event_from_page(link), published))
    if not docs:
        raise ParseError("FIA", "no decision-document PDF links found on the listing page")
    timed = sorted((d for d in docs if d.published_at), key=lambda d: d.published_at, reverse=True)
    return timed + [d for d in docs if not d.published_at]


async def fetch_listing() -> str:
    return (await http.get("FIA", LISTING_URL)).text


async def fetch_pdf(url: str) -> bytes:
    return (await http.get("FIA", url)).content
