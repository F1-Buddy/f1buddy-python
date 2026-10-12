"""Spec 05: session reminders and automatic weekend posts."""
import logging
from datetime import datetime, timedelta
from types import SimpleNamespace

import discord
import pandas as pd
import pytest
from discord import app_commands

from f1buddy import ctx
from f1buddy.cogs import setup as setup_cog
from f1buddy.cogs import watcher as w
from f1buddy.data import info, plots
from f1buddy.data import predictions as game
from f1buddy.errors import SourceError
from f1buddy.sources import fastf1_src, jolpica

from conftest import UTC, FakeInteraction, make_event
from test_fia import FakeChannel

RACE = datetime(2026, 3, 29, 5, tzinfo=UTC)                     # a Sunday
EVENT = make_event(2026, 3, "Japanese Grand Prix", "Japan", RACE)
SPRINT_EVENT = make_event(2026, 3, "Japanese Grand Prix", "Japan", RACE, "sprint_2024")
QUALI = EVENT.qualifying.start_utc


class FakeUser:
    def __init__(self, uid, blocked=False):
        self.id, self.blocked, self.got = uid, blocked, []

    async def send(self, embed):
        if self.blocked:
            raise discord.Forbidden(SimpleNamespace(status=403, reason="Forbidden"), "DMs closed")
        self.got.append(embed)


class FakeBot:
    def __init__(self, *things):
        self.users = {u.id: u for u in things if isinstance(u, FakeUser)}
        self.channels = {c.id: c for c in things if isinstance(c, FakeChannel)}

    def get_user(self, uid):
        return self.users.get(uid)

    def get_channel(self, cid):
        return self.channels.get(cid)


@pytest.fixture
def event(seasons):
    def install(e=EVENT):
        seasons({2026: [e]})
        return e
    return install


def minutes_before(slot_start, minutes):
    return slot_start - timedelta(minutes=minutes)


# ---------------------------------------------------------------- reminders

async def test_reminder_sent_once_at_the_lead_time(event):
    event()
    user = FakeUser(1)
    await w.set_reminder("user", 1, "Race only", 30)
    watcher = w.Watcher(FakeBot(user))
    await watcher.tick(minutes_before(RACE, 31))
    assert user.got == []
    await watcher.tick(minutes_before(RACE, 30))
    await watcher.tick(minutes_before(RACE, 29))
    assert len(user.got) == 1
    await w.Watcher(FakeBot(user)).tick(minutes_before(RACE, 28))     # a restart inside the window
    assert len(user.got) == 1
    embed = user.got[0]
    assert embed.title == "🇯🇵 Japanese Grand Prix — Race"
    stamp = int(RACE.timestamp())
    assert embed.description == f"Starts <t:{stamp}:R> (<t:{stamp}:t>)"


async def test_missed_window_is_skipped_not_sent_late(event):
    event()
    user = FakeUser(1)
    await w.set_reminder("user", 1, "Race only", 30)
    await w.Watcher(FakeBot(user)).tick(RACE + timedelta(minutes=1))
    assert user.got == []


async def test_session_filters_on_a_sprint_weekend(world, event):
    e = event(SPRINT_EVENT)
    racer, main, everything = FakeUser(1), FakeUser(2), FakeUser(3)
    await w.set_reminder("user", 1, "Race only", 15)
    await w.set_reminder("user", 2, "Qualifying, sprint and race", 15)
    await w.set_reminder("user", 3, "All sessions", 15)
    watcher = w.Watcher(FakeBot(racer, main, everything))
    for slot in e.sessions:
        await watcher.tick(minutes_before(slot.start_utc, 10))

    def sessions(user):
        return [embed.title.split(" — ")[1] for embed in user.got]
    assert sessions(racer) == ["Race"]
    assert sessions(main) == ["Sprint Qualifying", "Sprint", "Qualifying", "Race"]
    assert sessions(everything) == ["Practice 1", "Sprint Qualifying", "Sprint", "Qualifying", "Race"]
    assert w.wants("main", "Sprint Shootout") and not w.wants("main", "Practice 2")


async def test_remindme_off_removes_the_subscription(event, interaction):
    event()
    cog = w.Watcher(FakeBot(FakeUser(10)))
    await cog.remindme.callback(cog, interaction, "Race only", 60)
    assert interaction.response.sent[0]["ephemeral"] and "60 minutes" in interaction.response.sent[0]["content"]
    assert len(await ctx.db.q("SELECT * FROM reminder_subscriptions")) == 1
    await cog.remindme.callback(cog, interaction, "Off", 30)
    assert await ctx.db.q("SELECT * FROM reminder_subscriptions") == []
    await cog.tick(minutes_before(RACE, 10))
    assert cog.bot.users[10].got == []


async def test_blocked_dm_removes_only_that_subscription(event):
    event()
    blocked, fine = FakeUser(1, blocked=True), FakeUser(2)
    await w.set_reminder("user", 1, "Race only", 30)
    await w.set_reminder("user", 2, "Race only", 30)
    await w.Watcher(FakeBot(blocked, fine)).tick(minutes_before(RACE, 10))
    assert len(fine.got) == 1
    assert [r["target_id"] for r in await ctx.db.q("SELECT target_id FROM reminder_subscriptions")] == [2]


async def test_server_reminder_mentions_role_and_clears_dead_channel(event):
    event()
    channel = FakeChannel(5, 100)
    await ctx.db.set_setting(100, "reminder_channel_id", 5)
    await ctx.db.set_setting(100, "reminder_role_id", 77)
    await w.set_reminder("guild", 100, "Race only", 30)
    watcher = w.Watcher(FakeBot(channel))
    await watcher.tick(minutes_before(RACE, 20))
    assert channel.sent[0]["content"] == "<@&77>" and channel.sent[0]["embed"].title.endswith("Race")
    # a channel that keeps failing is cleared after three attempts
    await ctx.db.q("DELETE FROM reminders_sent")
    channel.fail = True
    for minute in (19, 18, 17):
        await watcher.tick(minutes_before(RACE, minute))
    assert await ctx.db.guilds_with("reminder_channel_id") == []


async def test_setup_commands_need_manage_server():
    cog = setup_cog.Setup()
    for command in (cog.fia, cog.reminders, cog.weekend):
        with pytest.raises(app_commands.MissingPermissions):
            for check in command.checks:
                check(FakeInteraction(manage_guild=False))
        assert all(check(FakeInteraction(manage_guild=True)) for check in command.checks)


async def test_setup_reminders_stores_everything(event):
    event()
    channel = SimpleNamespace(id=5, mention="<#5>", permissions_for=lambda me: SimpleNamespace(
        send_messages=True, attach_files=False, embed_links=True))
    interaction = FakeInteraction(manage_guild=True)
    interaction.guild.me = None
    cog = setup_cog.Setup()
    await cog.reminders.callback(cog, interaction, channel, SimpleNamespace(id=9, mention="<@&9>"), "Race only", 15)
    row = (await ctx.db.q("SELECT * FROM guild_settings"))[0]
    sub = (await ctx.db.q("SELECT * FROM reminder_subscriptions"))[0]
    assert (row["reminder_channel_id"], row["reminder_role_id"]) == (5, 9)
    assert (sub["kind"], sub["sessions"], sub["lead_minutes"]) == ("guild", "race", 15)
    assert "missing these permissions there: Attach Files" in interaction.response.sent[0]["content"]
    await cog.reminders.callback(cog, interaction, None)
    assert await ctx.db.q("SELECT * FROM reminder_subscriptions") == []


# ------------------------------------------------------------ weekend posts

def results(classified=True, n=20):
    return pd.DataFrame({
        "Abbreviation": [f"D{i:02d}" for i in range(1, n + 1)], "FullName": [f"Driver {i}" for i in range(1, n + 1)],
        "TeamId": "team", "Position": [float(i) for i in range(1, n)] + [float(n) if classified else float("nan")],
        "ClassifiedPosition": [str(i) for i in range(1, n)] + [str(n) if classified else ""],
        "Points": 0.0, "Q1": pd.Timedelta(seconds=90), "Q2": pd.NaT, "Q3": pd.NaT})


@pytest.fixture
def world(monkeypatch, event):
    """Fake every source the weekend jobs touch. `box.available` decides when results exist."""
    box = SimpleNamespace(available=lambda name, loads: True, loads=[], standings_round=2)

    async def load(year, round, name, **flags):
        box.loads.append(name)
        if not box.available(name, box.loads.count(name)):
            raise SourceError("FastF1", "not yet")
        return SimpleNamespace(results=results())

    async def fastest_lap(e):
        await ctx.db.cache_set(f"fl:{e.year}:{e.round}", {"code": "D01"})

    async def official(e):
        return "D01", ("D01", "D02", "D03")

    def rows(leader_first):
        order = ["a", "b", "c"] if leader_first else ["b", "a"]
        return [{"position": str(i), "points": str(30 - i), "Driver": {"driverId": d, "familyName": d.upper()},
                 "Constructor": {"constructorId": d, "name": d.upper()}, "Constructors": [{"constructorId": d}]}
                for i, d in enumerate(order, start=1)]

    async def standings(year, round=None):
        if round is not None:
            return {"round": round, "rows": rows(False)}
        return {"round": box.standings_round, "rows": rows(True)}

    async def nothing(*a, **k):
        return False
    monkeypatch.setattr(fastf1_src, "load", load)
    monkeypatch.setattr(info, "fastest_lap", fastest_lap)
    monkeypatch.setattr(game, "official_result", official)
    monkeypatch.setattr(jolpica, "driver_standings", standings)
    monkeypatch.setattr(jolpica, "constructor_standings", standings)
    monkeypatch.setattr(plots, "circuit_image", nothing)
    monkeypatch.setattr(info, "circuit_of", nothing)
    return box


async def weekend_bot(*guild_ids):
    channels = [FakeChannel(g + 1, g) for g in guild_ids]
    for channel in channels:
        await ctx.db.set_setting(channel.guild.id, "weekend_channel_id", channel.id)
    return w.Watcher(FakeBot(*channels)), channels


def titles(channel):
    return [e.title for e in channel.embeds]


async def test_preview_goes_out_once_on_thursday_noon(world, event, clock):
    event()
    thursday = datetime(2026, 3, 26, 12, tzinfo=UTC)
    clock(thursday)
    watcher, (one, two) = await weekend_bot(100, 200)
    await watcher.tick(thursday - timedelta(minutes=1))
    assert one.sent == []
    await watcher.tick(thursday)
    await watcher.tick(thursday + timedelta(minutes=1))
    assert titles(one) == titles(two) == ["Race Schedule for 🇯🇵 **Japanese GP** 🇯🇵"]
    assert w.preview_time(EVENT) == thursday


async def test_no_preview_in_a_week_without_a_race(world, event):
    event()
    watcher, (channel,) = await weekend_bot(100)
    await watcher.tick(datetime(2026, 3, 12, 12, tzinfo=UTC))     # a Thursday two weeks earlier
    assert channel.sent == []


async def test_race_post_waits_for_results(world, event):
    event()
    world.available = lambda name, loads: name != "Race" or loads >= 4
    watcher, (channel,) = await weekend_bot(100)
    start = w.first_check(EVENT.race)
    await watcher.tick(start - timedelta(minutes=1))
    assert "Race" not in world.loads                      # not before 30 minutes after the nominal end
    for i in range(3):
        await watcher.tick(start + timedelta(minutes=10 * i))
    await watcher.tick(start + timedelta(minutes=25))     # between checks: no extra load
    assert world.loads.count("Race") == 3 and not any("Race Results" in t for t in titles(channel))
    await watcher.tick(start + timedelta(minutes=30))
    await watcher.tick(start + timedelta(minutes=40))
    assert titles(channel).count("2026 Japanese Grand Prix Race Results") == 1
    assert await ctx.db.cache_get("fl:2026:3") == {"code": "D01"}        # the /fl cache is filled


def test_unclassified_entry_means_not_available():
    assert w.results_available(results())
    assert not w.results_available(results(classified=False))
    assert not w.results_available(results().iloc[0:0]) and not w.results_available(None)


async def test_gives_up_after_24_hours(world, event, caplog):
    event()
    world.available = lambda name, loads: name != "Race"
    watcher, (channel,) = await weekend_bot(100)
    with caplog.at_level(logging.WARNING):
        await watcher.tick(w.first_check(EVENT.race) + timedelta(hours=25))
    assert "giving up" in caplog.text and not any("Race Results" in t for t in titles(channel))
    world.available = lambda name, loads: True
    await watcher.tick(w.first_check(EVENT.race) + timedelta(hours=26))
    assert not any("Race Results" in t for t in titles(channel))


async def test_standings_wait_for_jolpica_and_show_changes(world, event):
    event()
    watcher, (channel,) = await weekend_bot(100)
    after = w.first_check(EVENT.race)
    await watcher.tick(after)
    assert "Standings after the Japanese Grand Prix" not in titles(channel)   # Jolpica still on round 2
    world.standings_round = 3
    await watcher.tick(after + timedelta(minutes=30))                         # hourly check: too soon
    assert "Standings after the Japanese Grand Prix" not in titles(channel)
    await watcher.tick(after + timedelta(hours=1))
    await watcher.tick(after + timedelta(hours=2))
    assert titles(channel).count("Standings after the Japanese Grand Prix") == 1
    embed = next(e for e in channel.embeds if e.title.startswith("Standings"))
    drivers = embed.fields[0].value.split("\n")
    assert drivers[0] == "**1.** A — 29 (▲1)" and drivers[1] == "**2.** B — 28 (▼1)"
    assert drivers[2] == "**3.** C — 27 (NEW)"


def test_position_changes():
    now = [{"position": "1", "id": "x"}, {"position": "2", "id": "y"}, {"position": "3", "id": "z"}]
    before = [{"position": "1", "id": "x"}, {"position": "5", "id": "z"}]
    assert [c for _, _, c in w.with_changes(now, before, lambda r: r["id"])] == ["–", "NEW", "▲2"]
    assert [c for _, _, c in w.with_changes(now, [], lambda r: r["id"], limit=2)] == ["–", "–"]


async def test_sprint_post_only_on_sprint_weekends(world, event):
    event(SPRINT_EVENT)
    watcher, (channel,) = await weekend_bot(100)
    await watcher.tick(w.first_check(SPRINT_EVENT.session("Sprint")))
    await watcher.tick(w.first_check(SPRINT_EVENT.race))
    assert "2026 Japanese Grand Prix Sprint Results" in titles(channel)
    assert "2026 Japanese Grand Prix Qualifying Results" in titles(channel)
    await ctx.db.q("DELETE FROM weekend_posts")
    await ctx.db.q("DELETE FROM cache")
    event(EVENT)
    watcher, (plain,) = await weekend_bot(300)
    await watcher.tick(w.first_check(EVENT.race))
    assert not any("Sprint" in t for t in titles(plain)) and "Sprint" not in world.loads[-3:]


async def test_restart_does_not_repeat_posts(world, event):
    event()
    watcher, (channel,) = await weekend_bot(100)
    world.standings_round = 3
    when = w.first_check(EVENT.race)
    await watcher.tick(when)
    count = len(channel.sent)
    again = w.Watcher(watcher.bot)
    await again.tick(when + timedelta(minutes=1))
    await again.tick(when + timedelta(hours=2))
    assert count == len(channel.sent) >= 3


async def test_server_enabling_mid_weekend_gets_only_later_posts(world, event, clock):
    event()
    watcher, (early,) = await weekend_bot(100)
    late = FakeChannel(201, 200)
    watcher.bot.channels[201] = late
    after_quali = w.first_check(EVENT.qualifying)
    await watcher.tick(after_quali)
    assert "2026 Japanese Grand Prix Qualifying Results" in titles(early)
    clock(after_quali)
    await ctx.db.set_setting(200, "weekend_channel_id", 201)
    await w.mark_weekend_seen(200, after_quali)                 # what /setup weekend does
    world.standings_round = 3
    await watcher.tick(w.first_check(EVENT.race))
    assert titles(late) == ["2026 Japanese Grand Prix Race Results", "Standings after the Japanese Grand Prix"]


async def test_weekend_posts_are_published_in_announcement_channels(world, event):
    event()
    channel = FakeChannel(11, 100, discord.ChannelType.news)
    await ctx.db.set_setting(100, "weekend_channel_id", 11)
    await w.Watcher(FakeBot(channel)).tick(w.first_check(EVENT.qualifying))
    assert channel.published == len(channel.sent) == 2      # the preview and the qualifying result
