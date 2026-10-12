from urllib.parse import unquote

from .. import ctx
from ..errors import SourceError
from . import http


async def photo(page_url: str | None) -> str | None:
    """Lead image of a Wikipedia page. Decoration only, so failure returns None."""
    if not page_url or "/wiki/" not in page_url:
        return None
    title = unquote(page_url.rsplit("/wiki/", 1)[1])
    key = f"wiki:photo:{title}"
    hit = await ctx.db.cache_get(key)
    if hit is not None:
        return hit or None
    try:
        data = await http.get_json("Wikipedia", f"https://en.wikipedia.org/api/rest_v1/page/summary/{title}")
    except SourceError:
        return None
    url = (data.get("originalimage") or data.get("thumbnail") or {}).get("source") or ""
    await ctx.db.cache_set(key, url, 30 * 86400)
    return url or None
