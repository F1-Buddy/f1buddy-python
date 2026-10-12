import asyncio

import httpx

from .. import __version__
from ..errors import SourceError

RETRY_DELAY = 2.0  # tests set this to 0
_client = None


def client() -> httpx.AsyncClient:
    global _client
    if _client is None:
        _client = httpx.AsyncClient(
            timeout=httpx.Timeout(30, connect=10),
            headers={"User-Agent": f"f1buddy/{__version__} (+https://github.com/F1-Buddy/f1buddy-python)"},
            follow_redirects=True,
        )
    return _client


def set_client(new):
    """Swap the client (tests pass one built on httpx.MockTransport)."""
    global _client
    _client = new


async def get(source: str, url: str, params=None) -> httpx.Response:
    """GET with one retry on a timeout or 5xx, and up to three waits on a 429. Raises SourceError."""
    detail = ""
    failures = throttled = 0
    while failures < 2 and throttled < 4:
        try:
            response = await client().get(url, params=params)
        except httpx.HTTPError as e:
            detail = f"{type(e).__name__}: {e}"
            failures += 1
            if failures < 2:
                await asyncio.sleep(RETRY_DELAY)
            continue
        if response.status_code < 400:
            return response
        detail = f"HTTP {response.status_code} for {response.url}"
        if response.status_code == 429:
            throttled += 1
            if throttled < 4:
                try:
                    wait = min(float(response.headers.get("Retry-After", 10)), 60)
                except ValueError:
                    wait = 10
                await asyncio.sleep(wait if RETRY_DELAY else 0)
        elif response.status_code >= 500:
            failures += 1
            if failures < 2:
                await asyncio.sleep(RETRY_DELAY)
        else:
            break
    raise SourceError(source, detail)


async def get_json(source, url, params=None):
    response = await get(source, url, params)
    try:
        return response.json()
    except ValueError as e:
        raise SourceError(source, f"invalid JSON from {url}") from e
