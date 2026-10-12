"""Spec 04: FIA documents."""
from datetime import datetime, timedelta
from types import SimpleNamespace

import discord
import httpx
import pymupdf
import pytest

from f1buddy import config, ctx
from f1buddy.cogs import fia as fia_cog
from f1buddy.errors import ParseError, SourceError, UserError
from f1buddy.sources import fia

from conftest import FIXTURES, UTC, FakeInteraction, three_race_season

LANDING = (FIXTURES / "fia" / "landing.html").read_text(encoding="utf8")
NOW = datetime(2026, 10, 12, 9, tzinfo=UTC)


def pdf(pages: int) -> bytes:
    doc = pymupdf.open()
    for i in range(pages):
        doc.new_page(width=200, height=200).insert_text((40, 100), f"Page {i + 1}")
    return doc.tobytes()


def listing(*docs):
    """A minimal listing page: (filename, title, 'DD.MM.YY HH:MM') per document."""
    items = "".join(
        f'<li><a href="/system/files/decision-document/{name}"><div>{title}</div>'
        f"<div>Published on <span>{when}</span> CET</div></a></li>" for name, title, when in docs)
    return f"<html><body><ul>{items}</ul></body></html>"


DOC_A = ("2026_test_grand_prix_-_a.pdf", "Doc 1 - A", "10.10.26 10:00")
DOC_B = ("2026_test_grand_prix_-_b.pdf", "Doc 2 - B", "10.10.26 11:00")
DOC_C = ("2026_test_grand_prix_-_c.pdf", "Doc 3 - C", "10.10.26 12:00")


class FakeChannel:
    def __init__(self, channel_id, guild_id, kind=discord.ChannelType.text, fail=False):
        self.id, self.type, self.fail = channel_id, kind, fail
        self.guild = SimpleNamespace(id=guild_id)
        self.sent, self.published = [], 0

    async def send(self, **kwargs):
        if self.fail:
            raise discord.HTTPException(SimpleNamespace(status=403, reason="Forbidden"), "nope")
        self.sent.append(kwargs)

        async def publish():
            self.published += 1
        return SimpleNamespace(publish=publish)

    @property
    def embeds(self):
        return [m["embed"] for m in self.sent if "embed" in m]


class FakeBot:
    def __init__(self, *channels):
        self.channels = {c.id: c for c in channels}
        self.alerts = []

    def get_channel(self, channel_id):
        return self.channels.get(channel_id)

    async def alert(self, message):
        self.alerts.append(message)


@pytest.fixture
def site(mock_http):
    """site.html is what the listing returns; site.pdfs maps filename -> bytes (default: 2 pages)."""
    box = SimpleNamespace(html=listing(DOC_A), pdfs={}, status=200)

    def handler(request):
        if request.url.path.endswith(".pdf"):
            return httpx.Response(200, content=box.pdfs.get(request.url.path.rsplit("/", 1)[1], pdf(2)))
        return httpx.Response(box.status, text=box.html)
    box.calls = mock_http(handler)
    return box


async def make_cog(*channels, configure=True):
    cog = fia_cog.Fia(FakeBot(*channels))
    if configure:
        for channel in channels:
            await fia_cog.set_channel(channel.guild.id, channel.id)
    return cog


# ------------------------------------------------------------------ parser

def test_parses_the_recorded_page():
    docs = fia.parse_listing(LANDING)
    assert len(docs) == 89                           # 90 entries on the page, one recalled without a link
    assert all(d.url.startswith("https://www.fia.com/system/files/decision-document/") and d.url.endswith(".pdf")
               for d in docs)
    assert all(d.title and d.published_at for d in docs)
    # ordered by publish time, not document number: Doc 52 was re-issued after the race
    assert docs[0].title == "Doc 52 - Sprint Scrutineering"
    points = docs[1]
    assert points.title == "Doc 91 - Championship Points" and points.event == "Singapore Grand Prix"
    assert points.published_at == datetime(2026, 10, 11, 15, 55, tzinfo=UTC)   # 17:55 CEST
    assert docs == sorted(docs, key=lambda d: d.published_at, reverse=True)
    assert not any("Recalled" in d.title for d in docs)


def test_parser_does_not_depend_on_tags_or_classes():
    restyled = (LANDING.replace('class="document-row', 'class="xyz').replace('class="title"', 'class="q"')
                .replace('class="published"', "").replace("<li", "<section").replace("</li>", "</section>")
                .replace('class="event-title', 'class="heading'))
    assert fia.parse_listing(restyled) == fia.parse_listing(LANDING)


def test_parser_edge_cases():
    with pytest.raises(ParseError):
        fia.parse_listing("<html><body><a href='/about.pdf'>About</a></body></html>")
    html = ('<h3>Monaco Grand Prix</h3><a href="/system/files/decision-document/odd%20name.pdf"></a>'
            '<a href="/system/files/decision-document/odd%20name.pdf">dup</a>')
    (doc,) = fia.parse_listing(html)
    assert (doc.title, doc.event, doc.published_at) == ("odd name", "Monaco Grand Prix", None)


def test_winter_time_is_cet():
    (doc,) = fia.parse_listing(listing(("x_-_y.pdf", "Doc", "11.12.26 17:55")))
    assert doc.published_at == datetime(2026, 12, 11, 16, 55, tzinfo=UTC)


# ----------------------------------------------------------------- polling

async def test_first_run_posts_nothing(site):
    channel = FakeChannel(1, 100)
    cog = await make_cog(channel)
    site.html = listing(DOC_A, DOC_B)
    assert await cog.poll_once(NOW)
    assert channel.sent == [] and len(await ctx.db.q("SELECT * FROM fia_documents")) == 2


async def test_new_documents_go_to_every_server_oldest_first(site):
    one, two = FakeChannel(1, 100), FakeChannel(2, 200, discord.ChannelType.news)
    cog = await make_cog(one, two)
    await cog.poll_once(NOW)
    site.html = listing(DOC_C, DOC_B, DOC_A)
    await cog.poll_once(NOW)
    await cog.poll_once(NOW)                                    # nothing new: no repeats
    for channel in (one, two):
        assert [e.title for e in channel.embeds] == ["Doc 2 - B", "Doc 3 - C"]
    embed = one.embeds[0]
    assert embed.url.endswith("_b.pdf") and "Test Grand Prix" in embed.description and "<t:" in embed.description
    assert len(one.sent[0]["files"]) == 2 and one.sent[0]["files"][0].filename == "page-001.png"
    assert (one.published, two.published) == (0, 2)             # only the announcement channel is published


async def test_failed_send_is_retried_without_duplicating_others(site):
    good, bad = FakeChannel(1, 100), FakeChannel(2, 200, fail=True)
    cog = await make_cog(good, bad)
    await cog.poll_once(NOW)
    site.html = listing(DOC_B, DOC_A)
    await cog.poll_once(NOW)
    assert len(good.embeds) == 1 and bad.sent == []
    bad.fail = False
    await cog.poll_once(NOW)
    assert len(good.embeds) == 1 and [e.title for e in bad.embeds] == ["Doc 2 - B"]


async def test_unreachable_channel_is_cleared_after_three_failures(site):
    bad = FakeChannel(2, 200, fail=True)
    cog = await make_cog(bad)
    await cog.poll_once(NOW)
    site.html = listing(DOC_B, DOC_A)
    for _ in range(3):
        await cog.poll_once(NOW)
    assert await ctx.db.guilds_with("fia_channel_id") == []


async def test_long_document_is_split_and_capped(site):
    channel = FakeChannel(1, 100)
    cog = await make_cog(channel)
    await cog.poll_once(NOW)
    site.pdfs["2026_test_grand_prix_-_b.pdf"] = pdf(25)
    site.html = listing(DOC_B, DOC_A)
    await cog.poll_once(NOW)
    assert [len(m.get("files", [])) for m in channel.sent] == [10, 10, 0]
    assert "embed" in channel.sent[0] and "embed" not in channel.sent[1]
    assert channel.sent[2]["content"].startswith("Showing 20 of 25 pages. Full document: https://www.fia.com/")


async def test_bad_pdf_becomes_a_link_after_three_attempts(site, monkeypatch):
    channel = FakeChannel(1, 100)
    cog = await make_cog(channel)
    await cog.poll_once(NOW)
    site.pdfs["2026_test_grand_prix_-_b.pdf"] = b"not a pdf"
    site.html = listing(DOC_C, DOC_B, DOC_A)
    await cog.poll_once(NOW)
    assert [e.title for e in channel.embeds] == ["Doc 3 - C"]   # the bad one doesn't block the queue
    await cog.poll_once(NOW)
    await cog.poll_once(NOW)
    assert channel.embeds[-1].title == "Doc 2 - B" and "files" not in channel.sent[-1]


async def test_parse_failure_alerts_once_then_recovers(site):
    cog = await make_cog(FakeChannel(1, 100))
    await cog.poll_once(NOW)
    site.html = "<html><body>redesigned</body></html>"
    for i in range(3):
        assert not await cog.poll_once(NOW + timedelta(minutes=5 * i))
    assert len(cog.bot.alerts) == 1 and "no longer parses" in cog.bot.alerts[0]
    site.html = listing(DOC_A)
    assert await cog.poll_once(NOW + timedelta(hours=1))
    assert cog.bot.alerts[-1] == "FIA documents: working again." and len(cog.bot.alerts) == 2


async def test_unreachable_alerts_after_six_failures(site):
    cog = await make_cog(FakeChannel(1, 100))
    site.status = 503
    for i in range(5):
        await cog.poll_once(NOW + timedelta(minutes=5 * i))
    assert cog.bot.alerts == []
    await cog.poll_once(NOW + timedelta(minutes=30))
    assert len(cog.bot.alerts) == 1 and "unreachable since" in cog.bot.alerts[0]


async def test_loop_survives_an_exception_and_keeps_its_interval(seasons, clock, monkeypatch):
    seasons({2026: []})
    clock(NOW)
    cog = await make_cog()
    runs = []

    async def boom(now):
        runs.append(now)
        raise RuntimeError("anything")
    monkeypatch.setattr(cog, "poll_once", boom)
    await cog.loop.coro(cog)                  # the exception is swallowed
    await cog.loop.coro(cog)                  # 0 minutes later: too early for the 30-minute interval
    assert len(runs) == 1
    clock(NOW + timedelta(minutes=30))
    await cog.loop.coro(cog)
    assert len(runs) == 2


def test_poll_interval():
    events = three_race_season()              # Japanese GP on Sunday 29 March 2026
    assert fia_cog.poll_interval(datetime(2026, 3, 28, 12, tzinfo=UTC), events) == timedelta(minutes=5)
    assert fia_cog.poll_interval(datetime(2026, 3, 26, 0, tzinfo=UTC), events) == timedelta(minutes=5)
    assert fia_cog.poll_interval(datetime(2026, 3, 30, 11, tzinfo=UTC), events) == timedelta(minutes=5)
    assert fia_cog.poll_interval(datetime(2026, 3, 30, 13, tzinfo=UTC), events) == timedelta(minutes=30)
    assert fia_cog.poll_interval(datetime(2026, 3, 24, 12, tzinfo=UTC), events) == timedelta(minutes=30)


async def test_server_enabling_later_gets_only_new_documents(site):
    early, late = FakeChannel(1, 100), FakeChannel(2, 200)
    cog = await make_cog(early, late, configure=False)
    await fia_cog.set_channel(100, 1)
    await cog.poll_once(NOW)
    site.html = listing(DOC_B, DOC_A)
    await cog.poll_once(NOW)
    await fia_cog.set_channel(200, 2)          # turned on after A and B exist
    site.html = listing(DOC_C, DOC_B, DOC_A)
    await cog.poll_once(NOW)
    assert [e.title for e in late.embeds] == ["Doc 3 - C"]
    assert [e.title for e in early.embeds] == ["Doc 2 - B", "Doc 3 - C"]


async def test_channel_from_environment_is_adopted(site):
    channel = FakeChannel(7, 700)
    ctx.config = config.Config(token="x", admin_ids=frozenset(), data_dir=ctx.config.data_dir, fia_channel_id=7)
    cog = await make_cog(channel, configure=False)
    await cog.poll_once(NOW)
    site.html = listing(DOC_B, DOC_A)
    await cog.poll_once(NOW)
    assert [e.title for e in channel.embeds] == ["Doc 2 - B"]


# ----------------------------------------------------------------- command

async def run_fiadoc(cog, doc=None):
    interaction = FakeInteraction()
    await cog.fiadoc.callback(cog, interaction, doc)
    return interaction.followup.sent


async def test_fiadoc_indexes_from_the_newest(site, clock):
    clock(NOW)
    site.html = listing(DOC_C, DOC_B, DOC_A)
    cog = await make_cog()
    latest = await run_fiadoc(cog)
    assert latest[0]["embed"].title == "Latest FIA Document" and "Doc 3 - C" in latest[0]["embed"].description
    assert (await run_fiadoc(cog, 2))[0]["embed"].title == "Doc 1 - A"
    for bad in (3, -1):
        with pytest.raises(UserError, match="Document doesn't exist!"):
            await run_fiadoc(cog, bad)


async def test_fiadoc_cached_pages_keep_their_order(site, clock):
    clock(NOW)
    site.pdfs[DOC_A[0]] = pdf(12)
    cog = await make_cog()
    first = await run_fiadoc(cog)
    requests = len(site.calls)
    second = await run_fiadoc(cog)

    def pages(sent):
        return [f.fp.read() for m in sent for f in m.get("files", [])]
    first_pages = pages(first)
    assert len(first_pages) == 12 and pages(second) == first_pages     # 1, 2, … 12, not 1, 10, 11, 12, 2
    assert len(site.calls) == requests                                 # fresh list and cached pages: no requests


async def test_fiadoc_answers_from_storage_when_the_site_is_down(site, clock):
    clock(NOW)
    cog = await make_cog()
    await run_fiadoc(cog)
    clock(NOW + timedelta(hours=1))
    site.status = 503
    sent = await run_fiadoc(cog)
    assert sent[0]["embed"].title == "Latest FIA Document"
    assert sent[-1]["content"] == "The FIA site couldn't be reached; this may not be the latest."


async def test_fiadoc_with_nothing_stored_and_site_down(site, clock):
    clock(NOW)
    site.status = 503
    with pytest.raises(SourceError):
        await run_fiadoc(await make_cog())
