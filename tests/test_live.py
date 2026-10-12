"""Spec 07 (recap only): /live."""
from datetime import datetime, timedelta

import httpx
import pytest

from f1buddy.cogs import live

from conftest import UTC, FakeInteraction, fixture_json, make_event

RACE = datetime(2026, 10, 11, 12, tzinfo=UTC)          # the recorded Singapore race
SINGAPORE = make_event(2026, 18, "Singapore Grand Prix", "Singapore", RACE)
AUSTIN = make_event(2026, 19, "United States Grand Prix", "United States", RACE + timedelta(days=14))


@pytest.fixture
def openf1(mock_http, seasons):
    seasons({2026: [SINGAPORE, AUSTIN]})
    live._snapshot.update(value=None, at=0.0)

    def handler(request):
        name = request.url.path.rsplit("/", 1)[1]
        return httpx.Response(200, json=fixture_json(f"openf1/{'sessions_latest' if name == 'sessions' else name}.json"))
    return mock_http(handler)


async def test_recap_of_the_last_session(openf1):
    embed = await live.snapshot(RACE + timedelta(days=1))
    assert embed.title == "🇸🇬 Singapore — Race" and embed.description.startswith("Finished <t:")
    fields = {f.name: f.value for f in embed.fields}
    assert fields["Track"] == "🏁 Chequered"
    assert fields["Weather"].startswith("Air ") and "Rain: " in fields["Weather"]
    order = fields["Order"].split("\n")
    assert len(order) == 10 and order[0] == "**1.** VER — Leader" and order[1] == "**2.** LEC — +7.335"
    assert len(fields["Race control"].split("\n")) == 5
    assert fields["Next"].startswith("United States Grand Prix — Practice 1 <t:")
    assert embed.footer.text == "Final"


async def test_session_in_progress_makes_no_data_request(openf1):
    embed = await live.snapshot(RACE + timedelta(minutes=30))
    assert embed.title == "🇸🇬 Singapore Grand Prix — Race"
    assert "Live data isn't enabled on this bot. A recap will be available after the session." in embed.description
    assert openf1 == []


async def test_recap_is_cached_and_calls_are_coalesced(openf1, clock):
    clock(RACE + timedelta(days=1))
    cog = live.Live()
    interactions = [FakeInteraction() for _ in range(10)]
    for interaction in interactions:
        await cog.live.callback(cog, interaction)
    assert all(i.followup.sent[0]["embed"].title == "🇸🇬 Singapore — Race" for i in interactions)
    assert len(openf1) == 5                       # one session lookup + four recap requests, not fifty
    live._snapshot.update(value=None, at=0.0)     # snapshot expired: the session lookup repeats, the recap doesn't
    await cog.live.callback(cog, FakeInteraction())
    assert len(openf1) == 6


def test_helpers():
    assert live.track_status([{"flag": "GREEN", "scope": "Track"}, {"flag": "YELLOW", "scope": "Sector"},
                              {"flag": "BLUE", "scope": "Driver"}]) == "🟢 Green"
    assert live.track_status([]) == "–"
    assert live.gap_text({"position": 4, "gap_to_leader": "+1 LAP"}) == "+1 LAP"
    assert live.gap_text({"position": 20, "dnf": True}) == "DNF"
    assert live.gap_text({"position": 2, "gap_to_leader": [0.3, 0.2, None]}) == "+0.200"
    assert live.running_session([SINGAPORE], RACE - timedelta(hours=1)) is None
    assert live.next_session([SINGAPORE], RACE + timedelta(days=1)) is None
