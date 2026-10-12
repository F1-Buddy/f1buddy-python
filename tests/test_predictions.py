"""Spec 06: predictions game."""
from datetime import datetime, timedelta
from types import SimpleNamespace

import pandas as pd
import pytest
from discord import app_commands

from f1buddy import ctx
from f1buddy.cogs import predictions as cog_module
from f1buddy.cogs import watcher as w
from f1buddy.data import info, plots
from f1buddy.data import predictions as game
from f1buddy.errors import UserError
from f1buddy.sources import fastf1_src, jolpica

from conftest import UTC, FakeInteraction, make_event
from test_fia import FakeChannel
from test_watcher import FakeBot

RACE = datetime(2026, 3, 29, 5, tzinfo=UTC)
EVENT = make_event(2026, 3, "Japanese Grand Prix", "Japan", RACE, "sprint_2024")
NEXT = make_event(2026, 4, "Bahrain Grand Prix", "Bahrain", RACE + timedelta(days=14))
QUALI = EVENT.qualifying.start_utc
SECOND = timedelta(seconds=1)
DRIVERS = [{"driverId": c.lower(), "code": c, "givenName": c, "familyName": f"{c}son"}
           for c in ("VER", "NOR", "LEC", "HAM", "PIA")]


@pytest.fixture(autouse=True)
def season(seasons, monkeypatch):
    seasons({2026: [EVENT, NEXT]})

    async def drivers(year):
        return DRIVERS
    monkeypatch.setattr(jolpica, "season_drivers", drivers)


def pred(pole="VER", p1="VER", p2="NOR", p3="LEC"):
    return {"pole": pole, "p1": p1, "p2": p2, "p3": p3}


ACTUAL = ("VER", ("VER", "NOR", "LEC"))


# --------------------------------------------------------- scoring function

def test_scoring():
    assert game.score(pred(), *ACTUAL) == (25, 3)                                  # everything right
    assert game.score(pred(pole="HAM"), *ACTUAL) == (20, 3)                        # pole wrong, podium exact
    assert game.score(pred(pole="HAM", p1="NOR", p2="LEC", p3="VER"), *ACTUAL) == (6, 0)   # rotated
    assert game.score(pred(p1="NOR", p2="LEC", p3="VER"), *ACTUAL) == (11, 0)      # rotated, pole right
    assert game.score(pred("HAM", "HAM", "PIA", "RUS"), *ACTUAL) == (0, 0)
    assert game.score(pred("HAM", "VER", "LEC", "PIA"), *ACTUAL) == (7, 1)         # exact, misplaced, absent
    assert game.score(pred(p1=None, p2=None, p3=None), *ACTUAL) == (5, 0)          # pole only
    assert game.score(pred(pole=None), *ACTUAL) == (20, 3)                         # podium only


# -------------------------------------------------------------------- locks

async def test_pole_locks_at_qualifying(clock):
    clock(QUALI - SECOND)
    event, row = await game.save_pole(100, 1, "ver")
    assert event.round == 3 and row["pole"] == "VER"
    clock(QUALI + SECOND)
    with pytest.raises(UserError, match="Pole predictions for Japanese Grand Prix are locked. "
                                        "You can still predict the podium until the race starts."):
        await game.save_pole(100, 1, "NOR")
    assert (await game.get(100, 1, EVENT))["pole"] == "VER"


async def test_podium_locks_at_the_race(clock):
    clock(QUALI + SECOND)
    event, _ = await game.save_podium(100, 1, "VER", "NOR", "LEC")
    assert event.round == 3
    clock(RACE - SECOND)
    event, row = await game.save_podium(100, 1, "NOR", "VER", "LEC")
    assert event.round == 3 and (row["p1"], row["p2"]) == ("NOR", "VER")
    clock(RACE + SECOND)
    event, _ = await game.save_podium(100, 1, "HAM", "VER", "LEC")     # now applies to the next race
    assert event.round == 4 and (await game.get(100, 1, EVENT))["p1"] == "NOR"
    event, _ = await game.save_pole(100, 1, "HAM")                     # as does pole
    assert event.round == 4


async def test_sprint_sessions_never_lock_anything(clock):
    sprint_quali = EVENT.session("Sprint Qualifying").start_utc
    sprint = EVENT.session("Sprint").start_utc
    assert sprint_quali < sprint < QUALI < RACE
    clock(sprint + timedelta(minutes=30))
    assert (await game.save_pole(100, 1, "VER"))[0].round == 3
    assert (await game.save_podium(100, 1, "VER", "NOR", "LEC"))[0].round == 3
    assert game.lock_time(EVENT, "pole") == QUALI and game.lock_time(EVENT, "podium") == RACE


# ----------------------------------------------------------------- commands

async def test_parts_are_saved_independently(clock):
    clock(QUALI - SECOND)
    await game.save_podium(100, 1, "VER", "NOR", "LEC")
    assert (await game.get(100, 1, EVENT))["pole"] is None             # podium alone leaves pole empty
    await game.save_pole(100, 1, "HAM")
    await game.save_pole(100, 1, "PIA")                                # later value wins
    await game.save_podium(100, 1, "LEC", "NOR", "VER")
    rows = await ctx.db.q("SELECT * FROM predictions")
    assert len(rows) == 1
    assert (rows[0]["pole"], rows[0]["p1"], rows[0]["p2"], rows[0]["p3"]) == ("PIA", "LEC", "NOR", "VER")


async def test_validation(clock):
    clock(QUALI - SECOND)
    with pytest.raises(UserError, match="Pick three different drivers for the podium."):
        await game.save_podium(100, 1, "VER", "ver", "LEC")
    with pytest.raises(UserError, match='Driver "senna" isn\'t entered in the 2026 season.'):
        await game.save_pole(100, 1, "senna")
    assert await ctx.db.q("SELECT * FROM predictions") == []
    cog = cog_module.Predictions()
    with pytest.raises(UserError, match="Predictions are per server. Use this in a server."):
        await cog.pole.callback(cog, FakeInteraction(guild_id=None), "VER")


async def test_predict_reply_shows_both_parts(clock):
    clock(QUALI - SECOND)
    cog, interaction = cog_module.Predictions(), FakeInteraction(user_id=1)
    await cog.pole.callback(cog, interaction, "VER")
    reply = interaction.response.sent[0]
    assert reply["ephemeral"] and reply["embed"].title == "Your prediction — Japanese Grand Prix"
    assert "**Pole:** VER (locks <t:" in reply["embed"].description
    assert "**Podium:** not set (locks <t:" in reply["embed"].description


async def view(user_id, when, clock):
    clock(when)
    cog, interaction = cog_module.Predictions(), FakeInteraction(user_id=user_id)
    await cog.predictions.callback(cog, interaction)
    reply = interaction.response.sent[0]
    return reply["embed"].description, reply["ephemeral"]


async def test_visibility_follows_each_lock(clock):
    clock(QUALI - timedelta(hours=1))
    await game.save_pole(100, 1, "VER")
    await game.save_podium(100, 1, "VER", "NOR", "LEC")
    await game.save_pole(100, 2, "HAM")
    await game.save_podium(100, 2, "HAM", "PIA", "LEC")

    before, private = await view(1, QUALI - SECOND, clock)
    assert private and "<@1>: pole VER" in before and "<@2>" not in before
    assert "2 member(s) have entered a prediction" in before

    between, private = await view(1, QUALI + SECOND, clock)
    assert private and "<@2>: pole HAM · podium –" in between          # pole visible, podium still hidden
    assert "<@1>: pole VER · podium 🥇 VER · 🥈 NOR · 🥉 LEC" in between
    assert "2 member(s) have entered a podium" in between

    after, private = await view(1, RACE + SECOND, clock)
    assert not private and "<@2>: pole HAM · podium 🥇 HAM · 🥈 PIA · 🥉 LEC" in after


async def test_servers_are_separate(clock):
    clock(QUALI - SECOND)
    await game.save_pole(100, 1, "VER")
    await game.save_pole(200, 2, "HAM")
    await game.score_round(EVENT, *ACTUAL)
    assert [r["user_id"] for r in await game.for_event(100, EVENT)] == [1]
    assert [e[1] for e in await game.leaderboard(200, 2026)] == [2]


# ------------------------------------------------------------- leaderboard

async def test_leaderboard_totals_ties_and_own_row(clock):
    rows = [(u, 30 - u, 1) for u in range(1, 15)]          # 14 members, strictly ordered
    rows[2] = (3, 29, 0)                                    # user 3 ties user 1 on points...
    rows[0] = (1, 29, 2)                                    # ...but user 1 has more exact hits
    for user, points, exact in rows:
        await ctx.db.q("INSERT INTO prediction_scores VALUES (100, ?, 'f1', 2026, 1, ?, ?)", user, points - 10, exact)
        await ctx.db.q("INSERT INTO prediction_scores VALUES (100, ?, 'f1', 2026, 2, 10, 0)", user)
    board = await game.leaderboard(100, 2026)
    assert [(e[0], e[1], e[2]) for e in board[:3]] == [(1, 1, 29), (1, 3, 29), (3, 2, 28)]   # shared rank
    assert all(e[3] == 2 for e in board)
    embed = cog_module.leaderboard_embed(2026, "Test Server", board, viewer_id=14)
    lines = embed.description.split("\n")
    assert len(lines) == 12 and lines[10] == "…" and lines[11].startswith("**14.** <@14> — 16 pts (2 races)")
    assert embed.title == "2026 Predictions Leaderboard — Test Server"
    empty = cog_module.leaderboard_embed(2026, "S", [], 1)
    assert empty.description == "No predictions have been scored yet this season."


# --------------------------------------------------------------------- flow

async def test_scoring_is_idempotent_and_rescore_counts_changes(clock):
    clock(QUALI - SECOND)
    await game.save_pole(100, 1, "VER")
    await game.save_podium(100, 1, "VER", "NOR", "LEC")
    await game.save_pole(100, 2, "HAM")
    assert await game.score_round(EVENT, *ACTUAL) == {100: 2}
    assert await game.score_round(EVENT, *ACTUAL) == {100: 0}
    scores = {r["user_id"]: (r["points"], r["exact_hits"]) for r in await ctx.db.q("SELECT * FROM prediction_scores")}
    assert scores == {1: (25, 3), 2: (0, 0)}
    # a post-race penalty swaps second and third
    assert await game.score_round(EVENT, "VER", ("VER", "LEC", "NOR")) == {100: 1}
    assert (await game.actual(EVENT))["podium"] == ["VER", "LEC", "NOR"]


async def test_rescore_command(clock, monkeypatch):
    clock(RACE + timedelta(days=1))
    cog = cog_module.Predictions()
    with pytest.raises(app_commands.MissingPermissions):
        for check in cog.rescore.checks:
            check(FakeInteraction(manage_guild=False))

    async def official(event):
        return ACTUAL
    monkeypatch.setattr(game, "official_result", official)
    await ctx.db.q("INSERT INTO predictions (guild_id,user_id,year,round,pole,updated_at) VALUES (100,1,2026,3,'VER',0)")
    interaction = FakeInteraction(manage_guild=True)
    await cog.rescore.callback(cog, interaction, "3")
    assert interaction.followup.sent[0]["content"] == \
        "Rescored Japanese Grand Prix: 1 score(s) changed in this server."


async def test_official_result_reads_pole_from_qualifying(monkeypatch):
    async def load(year, round, name, **flags):
        assert flags.get("fresh")
        order = ["HAM", "VER", "NOR", "LEC"] if name == "Qualifying" else ["VER", "NOR", "LEC", "HAM"]
        return SimpleNamespace(results=pd.DataFrame({"Abbreviation": order[::-1], "Position": [4.0, 3.0, 2.0, 1.0]}))
    monkeypatch.setattr(fastf1_src, "load", load)
    assert await game.official_result(EVENT) == ("HAM", ("VER", "NOR", "LEC"))


async def test_race_result_scores_every_server_and_posts_once(clock, monkeypatch):
    clock(QUALI - SECOND)
    await game.save_pole(100, 1, "VER")           # server with a weekend channel
    await game.save_pole(200, 2, "VER")           # server without one
    channel = FakeChannel(101, 100)
    await ctx.db.set_setting(100, "weekend_channel_id", 101)

    async def load(year, round, name, **flags):
        codes = ["VER", "NOR", "LEC"]
        return SimpleNamespace(results=pd.DataFrame({
            "Abbreviation": codes, "FullName": codes, "TeamId": "t", "Position": [1.0, 2.0, 3.0],
            "ClassifiedPosition": ["1", "2", "3"], "Points": [25.0, 18.0, 15.0],
            "Q1": pd.NaT, "Q2": pd.NaT, "Q3": pd.NaT}))

    async def nothing(*a, **k):
        return None
    monkeypatch.setattr(fastf1_src, "load", load)
    monkeypatch.setattr(info, "fastest_lap", nothing)
    monkeypatch.setattr(info, "circuit_of", nothing)
    monkeypatch.setattr(plots, "circuit_image", nothing)

    async def standings(year, round=None):
        return {"round": 0, "rows": []}
    monkeypatch.setattr(jolpica, "driver_standings", standings)

    watcher = w.Watcher(FakeBot(channel))
    when = w.first_check(EVENT.race)
    clock(when)
    await watcher.tick(when)
    await watcher.tick(when + timedelta(minutes=20))
    scored = {(r["guild_id"], r["user_id"]): r["points"] for r in await ctx.db.q("SELECT * FROM prediction_scores")}
    assert scored == {(100, 1): 5, (200, 2): 5}
    posts = [e for e in channel.embeds if e.title == "Prediction results — Japanese Grand Prix"]
    assert len(posts) == 1 and "**Pole:** VER" in posts[0].description
    assert posts[0].fields[0].value == "<@1> — 5 pts"
    # once scored, /predictions shows points and the actual result, and moves on to the next race by default
    cog, interaction = cog_module.Predictions(), FakeInteraction(user_id=1)
    await cog.predictions.callback(cog, interaction, "3")
    text = interaction.response.sent[0]["embed"].description
    assert text.startswith("**Pole:** VER · **Podium:** VER · NOR · LEC") and "**5 pts**" in text
    assert (await game.current_event(when)).round == 4
