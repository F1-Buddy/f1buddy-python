import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

import httpx
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from f1buddy import ctx, util  # noqa: E402
from f1buddy.config import Config  # noqa: E402
from f1buddy.db import Database  # noqa: E402
from f1buddy.series import Event, SessionSlot, f1  # noqa: E402
from f1buddy.sources import http, jolpica  # noqa: E402

FIXTURES = Path(__file__).parent / "fixtures"
UTC = timezone.utc


def fixture_json(name):
    return json.loads((FIXTURES / name).read_text(encoding="utf8"))


@pytest.fixture(autouse=True)
def app(tmp_path, monkeypatch):
    """Fresh in-memory database and config for every test; no network, no waiting."""
    (tmp_path / "plots").mkdir()
    ctx.config = Config(token="x", admin_ids=frozenset({1}), data_dir=tmp_path)
    ctx.db = Database()
    monkeypatch.setattr(http, "RETRY_DELAY", 0)
    monkeypatch.setattr(jolpica, "MIN_INTERVAL", 0)

    def refuse(request):
        raise AssertionError(f"unexpected network request: {request.url}")
    http.set_client(httpx.AsyncClient(transport=httpx.MockTransport(refuse)))
    yield
    ctx.db.close()
    http.set_client(None)


@pytest.fixture
def mock_http():
    """mock_http(handler) installs a handler(request) -> httpx.Response and returns the list of requests made."""
    def install(handler):
        calls = []

        def wrapped(request):
            calls.append(request)
            return handler(request)
        http.set_client(httpx.AsyncClient(transport=httpx.MockTransport(wrapped)))
        return calls
    return install


@pytest.fixture
def clock(monkeypatch):
    """clock(datetime) fixes util.now()."""
    def set_now(when):
        monkeypatch.setattr(util, "now", lambda: when)
    return set_now


def make_event(year, round, name, country, race_start, fmt="conventional"):
    """A weekend whose sessions are placed relative to the race start."""
    layouts = {
        "conventional": [("Practice 1", 50), ("Practice 2", 46), ("Practice 3", 26), ("Qualifying", 22)],
        "sprint_2021": [("Practice 1", 50), ("Qualifying", 46), ("Practice 2", 26), ("Sprint", 22)],
        "sprint_2023": [("Practice 1", 50), ("Qualifying", 46), ("Sprint Shootout", 26), ("Sprint", 22)],
        "sprint_2024": [("Practice 1", 50), ("Sprint Qualifying", 46), ("Sprint", 26), ("Qualifying", 22)],
    }
    slots = [SessionSlot(n, race_start - timedelta(hours=h)) for n, h in layouts[fmt]]
    slots.append(SessionSlot("Race", race_start))
    return Event("f1", year, round, name, country, name.replace(" Grand Prix", ""), tuple(slots))


@pytest.fixture
def seasons(monkeypatch):
    """seasons({2026: [events]}) replaces the F1 schedule."""
    def install(by_year):
        async def schedule(year):
            return by_year.get(year, [])
        monkeypatch.setattr(f1, "season_schedule", schedule)
    return install


def three_race_season(year=2026):
    return [
        make_event(year, 1, "Australian Grand Prix", "Australia", datetime(year, 3, 8, 4, tzinfo=UTC)),
        make_event(year, 2, "Chinese Grand Prix", "China", datetime(year, 3, 15, 7, tzinfo=UTC), "sprint_2024"),
        make_event(year, 3, "Japanese Grand Prix", "Japan", datetime(year, 3, 29, 5, tzinfo=UTC)),
    ]


class FakeResponse:
    def __init__(self):
        self.deferred = False
        self.sent = []

    def is_done(self):
        return self.deferred or bool(self.sent)

    async def defer(self, **kwargs):
        self.deferred = True

    async def send_message(self, *args, **kwargs):
        self.sent.append(kwargs | ({"content": args[0]} if args else {}))


class FakeFollowup:
    def __init__(self):
        self.sent = []

    async def send(self, *args, **kwargs):
        self.sent.append(kwargs | ({"content": args[0]} if args else {}))
        return SimpleNamespace(id=len(self.sent), edit=None)


class FakeInteraction:
    """Records defer and send calls, which is all a command callback touches."""

    def __init__(self, user_id=10, guild_id=100, manage_guild=False, client=None):
        self.response = FakeResponse()
        self.followup = FakeFollowup()
        self.user = SimpleNamespace(id=user_id, mention=f"<@{user_id}>", display_name=f"user{user_id}", bot=False)
        self.guild_id = guild_id
        self.guild = SimpleNamespace(id=guild_id, name="Test Server") if guild_id else None
        self.namespace = SimpleNamespace()
        self.client = client
        self.permissions = SimpleNamespace(manage_guild=manage_guild)

    async def delete_original_response(self):
        pass

    @property
    def replies(self):
        return self.response.sent + self.followup.sent


@pytest.fixture
def interaction():
    return FakeInteraction()
