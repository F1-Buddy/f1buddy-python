"""/live (spec 07, recap only): a summary of the most recent session.

Live timing needs a paid data source, so during a session this only says when the recap will be ready.
"""
import time
from datetime import datetime, timedelta

import discord
from discord import app_commands
from discord.ext import commands

from .. import ctx, util
from ..data import params
from ..errors import SourceError
from ..render import embeds
from ..sources import openf1

SNAPSHOT_SECONDS = 10
FLAGS = {"GREEN": "🟢 Green", "YELLOW": "🟡 Yellow", "DOUBLE YELLOW": "🟡 Double yellow", "RED": "🔴 Red flag",
         "CHEQUERED": "🏁 Chequered", "CLEAR": "🟢 Green"}
_snapshot = {"at": 0.0, "value": None}


def running_session(events, now):
    """(event, slot) if a session is on track right now, allowing 30 minutes of overrun."""
    for event in events:
        for slot in event.sessions:
            if slot.start_utc <= now <= slot.end_utc + timedelta(minutes=30):
                return event, slot
    return None


def next_session(events, now):
    upcoming = [(slot.start_utc, event, slot) for event in events for slot in event.sessions if slot.start_utc > now]
    return min(upcoming, key=lambda x: x[0])[1:] if upcoming else None


def track_status(messages) -> str:
    """The last flag shown to the whole track."""
    for m in reversed(messages):
        if m.get("flag") in FLAGS and (m.get("scope") in ("Track", None) or m["flag"] == "CHEQUERED"):
            return FLAGS[m["flag"]]
    return "–"


def gap_text(row) -> str:
    if row.get("dsq"):
        return "DSQ"
    if row.get("dns"):
        return "DNS"
    if row.get("dnf"):
        return "DNF"
    gap = row.get("gap_to_leader")
    if isinstance(gap, list):          # qualifying: one gap per segment
        gap = next((g for g in reversed(gap) if g is not None), None)
    if row.get("position") == 1 or gap in (0, None):
        return "Leader" if row.get("position") == 1 else "–"
    return f"+{gap:.3f}" if isinstance(gap, (int, float)) else str(gap)


def recap_embed(session, data, upcoming) -> discord.Embed:
    drivers = {d["driver_number"]: d for d in data["drivers"]}
    ended = datetime.fromisoformat(session["date_end"])
    flag = util.country_flag(session.get("country_name"))
    embed = embeds.make(f"{flag} {session.get('country_name', '')} — {session['session_name']}".strip(),
                        f"Finished {util.ts(ended, 'R')}", "Final")
    embed.add_field(name="Track", value=track_status(data["race_control"]), inline=True)
    if data["weather"]:
        w = data["weather"][-1]
        embed.add_field(name="Weather", inline=True, value=(
            f"Air {w['air_temperature']:.0f} °C · Track {w['track_temperature']:.0f} °C\n"
            f"Humidity {w['humidity']:.0f}% · Wind {w['wind_speed']:.1f} m/s @ {w['wind_direction']}°\n"
            f"Rain: {'yes' if w.get('rainfall') else 'no'}"))
    order = sorted((r for r in data["result"] if r.get("position")), key=lambda r: r["position"])[:10]
    if order:
        embed.add_field(name="Order", inline=False, value="\n".join(
            f"**{r['position']}.** {drivers.get(r['driver_number'], {}).get('name_acronym', r['driver_number'])}"
            f" — {gap_text(r)}" for r in order))
    recent = [m for m in data["race_control"] if m.get("message")][-5:]
    if recent:
        embed.add_field(name="Race control", inline=False, value=util.clamp("\n".join(
            f"{util.ts(datetime.fromisoformat(m['date']), 'T')} {m['message']}" for m in recent), 1024))
    if upcoming:
        event, slot = upcoming
        embed.add_field(name="Next", value=f"{event.name} — {slot.name} {util.ts(slot.start_utc, 'R')}",
                        inline=False)
    return embed


async def snapshot(now) -> discord.Embed:
    events = await params.season(now.year)
    upcoming = next_session(events, now)
    running = running_session(events, now)
    if running:
        event, slot = running
        return embeds.make(
            f"{util.country_flag(event.country)} {event.name} — {slot.name}".strip(),
            f"Started {util.ts(slot.start_utc, 'R')}.\n\nLive data isn't enabled on this bot. "
            "A recap will be available after the session.")
    session = await openf1.latest_session()
    if session is None:
        raise SourceError("OpenF1", "no session found")
    key = f"live:recap:{session['session_key']}"
    data = await ctx.db.cache_get(key)
    if data is None:
        data = await openf1.recap(session["session_key"])
        await ctx.db.cache_set(key, data, 3600)
    return recap_embed(session, data, upcoming)


class Live(commands.Cog):
    category = "Live"

    @app_commands.command(name="live", description="Recap of the most recent session, and when the next one starts")
    async def live(self, interaction: discord.Interaction):
        await interaction.response.defer()
        # many people ask at once after a session; build the reply once every few seconds
        if _snapshot["value"] is None or time.monotonic() - _snapshot["at"] > SNAPSHOT_SECONDS:
            _snapshot.update(value=await snapshot(util.now()), at=time.monotonic())
        await interaction.followup.send(embed=_snapshot["value"])


async def setup(bot):
    await bot.add_cog(Live())
