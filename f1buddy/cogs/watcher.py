"""Schedule watcher (spec 05): session reminders, automatic weekend posts, and the jobs that hang off them."""
import logging
import time
from datetime import timedelta
from typing import Literal, Optional

import discord
from discord import app_commands
from discord.ext import commands, tasks

from .. import ctx, util
from ..data import info, params, plots
from ..data import predictions as game
from ..errors import SourceError
from ..render import embeds
from ..series import Event
from ..sources import fastf1_src, jolpica
from . import common
from . import predictions as predictions_cog

log = logging.getLogger(__name__)
SERIES = "f1"
SESSION_SETS = {"All sessions": "all", "Qualifying, sprint and race": "main", "Race only": "race"}
RESULT_KINDS = {"sprint": "Sprint", "qualifying": "Qualifying", "race": "Race"}
CHECK_EVERY = timedelta(minutes=10)
GIVE_UP_AFTER = timedelta(hours=24)


# ------------------------------------------------------------ pure helpers

def wants(sessions: str, name: str) -> bool:
    if sessions == "all":
        return True
    if sessions == "race":
        return name == "Race"
    return name == "Race" or any(word in name for word in ("Qualifying", "Shootout", "Sprint"))


def reminder_embed(event: Event, slot) -> discord.Embed:
    flag = util.country_flag(event.country)
    return embeds.make(f"{flag} {event.name} — {slot.name}".strip(),
                       f"Starts {util.ts(slot.start_utc, 'R')} ({util.ts(slot.start_utc, 't')})")


def preview_time(event: Event):
    """Thursday 12:00 UTC of race week."""
    day = event.race.start_utc.replace(hour=12, minute=0, second=0, microsecond=0)
    return day - timedelta(days=(day.weekday() - 3) % 7)


def first_check(slot):
    """When to start looking for a session's results: 30 minutes after its nominal end."""
    return slot.end_utc + timedelta(minutes=30)


def results_available(results) -> bool:
    """A results table counts once every entry has a classified position or status."""
    if results is None or len(results) == 0:
        return False
    classified = results.get("ClassifiedPosition")
    for i, position in enumerate(results["Position"]):
        text = "" if classified is None else str(classified.iloc[i] or "").strip()
        if position != position and not text:   # NaN position and no status
            return False
    return True


def with_changes(now_rows, previous_rows, ident, limit=None):
    """[(position, row, change)] where change is ▲n, ▼n, – or NEW against the previous round."""
    before = {ident(r): int(r["position"]) for r in previous_rows if str(r.get("position", "")).isdigit()}
    out = []
    for row in now_rows[:limit]:
        if not str(row.get("position", "")).isdigit():
            continue
        position, old = int(row["position"]), before.get(ident(row))
        if not previous_rows:
            change = "–"
        elif old is None:
            change = "NEW"
        else:
            change = "–" if old == position else f"▲{old - position}" if old > position else f"▼{position - old}"
        out.append((position, row, change))
    return out


def standings_embed(event, drivers, constructors) -> discord.Embed:
    embed = embeds.make(f"Standings after the {event.name}")
    embeds.columns(embed, ("Drivers", [
        f"**{pos}.** {embeds.team_emoji(r['Constructors'][-1]['constructorId']) if r.get('Constructors') else ''} "
        f"{r['Driver']['familyName']} — {util.fmt_points(r['points'])} ({change})".replace("  ", " ")
        for pos, r, change in drivers]))
    embeds.columns(embed, ("Constructors", [
        f"**{pos}.** {embeds.team_emoji(r['Constructor']['constructorId'])} {r['Constructor']['name']} — "
        f"{util.fmt_points(r['points'])} ({change})".replace("  ", " ")
        for pos, r, change in constructors]))
    return embed


async def is_done(event, kind):
    """'ok', 'gave_up' or None: whether a weekend job for an event has been settled."""
    return await ctx.db.cache_get(f"weekend:{event.year}:{event.round}:{kind}")


class Watcher(commands.Cog):
    category = "Reminders"

    def __init__(self, bot):
        self.bot = bot
        self.next_check = {}        # (year, round, kind) -> when to look for results again
        self.channel_failures = {}  # (setting, guild id) -> consecutive failed sends

    async def cog_load(self):
        self.loop.start()

    async def cog_unload(self):
        self.loop.cancel()

    @tasks.loop(minutes=1)
    async def loop(self):
        try:
            await self.tick(util.now())
        except Exception:
            log.exception("watcher tick failed")

    @loop.before_loop
    async def _wait(self):
        await self.bot.wait_until_ready()

    async def tick(self, now):
        events = await params.season(now.year)
        try:
            events = events + await params.season(now.year + 1)
        except SourceError:
            pass
        await self.send_reminders(now, events)
        for event in events:
            if event.race and now - timedelta(days=5) <= event.race.start_utc <= now + timedelta(days=7):
                try:
                    await self.weekend(now, event)
                except Exception:
                    log.exception("weekend jobs for round %s failed", event.round)

    # ----------------------------------------------------------- reminders
    async def send_reminders(self, now, events):
        soon = [(e, s) for e in events for s in e.sessions if timedelta(0) < s.start_utc - now <= timedelta(hours=1)]
        if not soon:
            return
        subscriptions = await ctx.db.q("SELECT * FROM reminder_subscriptions WHERE series = ?", SERIES)
        for event, slot in soon:
            for sub in subscriptions:
                if not wants(sub["sessions"], slot.name):
                    continue
                if slot.start_utc - now > timedelta(minutes=sub["lead_minutes"]):
                    continue
                key = (sub["id"], event.year, event.round, slot.name)
                if await ctx.db.one("SELECT 1 FROM reminders_sent WHERE subscription_id=? AND year=? AND round=? "
                                    "AND session_name=?", *key):
                    continue
                try:
                    if await self.deliver_reminder(sub, reminder_embed(event, slot)):
                        await ctx.db.q("INSERT OR IGNORE INTO reminders_sent VALUES (?,?,?,?)", *key)
                except Exception:
                    log.exception("reminder for subscription %s failed", sub["id"])

    async def deliver_reminder(self, sub, embed) -> bool:
        if sub["kind"] == "user":
            try:
                user = self.bot.get_user(sub["target_id"]) or await self.bot.fetch_user(sub["target_id"])
                await user.send(embed=embed)
            except (discord.Forbidden, discord.NotFound):
                # DMs closed, or no shared server: stop trying
                await ctx.db.q("DELETE FROM reminder_subscriptions WHERE id = ?", sub["id"])
                return False
            return True
        settings = await ctx.db.one("SELECT * FROM guild_settings WHERE guild_id = ?", sub["target_id"])
        if not settings or not settings["reminder_channel_id"]:
            return False
        role = settings["reminder_role_id"]
        return await self.send_to(sub["target_id"], "reminder_channel_id", settings["reminder_channel_id"],
                                  embed=embed, content=f"<@&{role}>" if role else None)

    async def send_to(self, guild_id, setting, channel_id, publish=False, **kwargs) -> bool:
        """Send to a server's configured channel. Three failures in a row clears the setting."""
        channel = self.bot.get_channel(channel_id)
        try:
            if channel is None:
                raise LookupError("channel not found")
            message = await channel.send(**{k: v for k, v in kwargs.items() if v is not None})
        except (discord.HTTPException, LookupError) as e:
            count = self.channel_failures[(setting, guild_id)] = self.channel_failures.get((setting, guild_id), 0) + 1
            log.warning("send to server %s (%s) failed: %s", guild_id, setting, e)
            if count >= 3:
                await ctx.db.set_setting(guild_id, setting, None)
                self.channel_failures.pop((setting, guild_id))
            return False
        self.channel_failures.pop((setting, guild_id), None)
        if publish and getattr(channel, "type", None) == discord.ChannelType.news:
            try:
                await message.publish()
            except discord.HTTPException:
                pass
        return True

    # ------------------------------------------------------- weekend posts
    async def done(self, event, kind):
        return await is_done(event, kind)

    async def set_done(self, event, kind, value="ok"):
        await ctx.db.cache_set(f"weekend:{event.year}:{event.round}:{kind}", value)

    async def post_all(self, event, kind, build):
        """Send a weekend post to every server that hasn't had it. `build` returns send() keyword arguments."""
        for guild in await ctx.db.guilds_with("weekend_channel_id"):
            key = (guild["guild_id"], SERIES, event.year, event.round, kind)
            if await ctx.db.one("SELECT 1 FROM weekend_posts WHERE guild_id=? AND series=? AND year=? AND round=? "
                                "AND kind=?", *key):
                continue
            kwargs = await build(guild["guild_id"])
            if kwargs is None:
                continue
            if await self.send_to(guild["guild_id"], "weekend_channel_id", guild["weekend_channel_id"],
                                  publish=True, **kwargs):
                await ctx.db.q("INSERT OR IGNORE INTO weekend_posts VALUES (?,?,?,?,?,?)", *key, int(time.time()))

    async def weekend(self, now, event):
        race = event.race
        # circuit image for /schedule, from the Monday of race week
        if race.start_utc - timedelta(days=6) <= now < race.start_utc and not await self.done(event, "circuit"):
            await self.set_done(event, "circuit")
            try:
                await plots.circuit_image(event)
            except Exception:
                log.exception("circuit image failed")

        if preview_time(event) <= now < race.start_utc:
            await self.set_done(event, "preview")
            await self.post_all(event, "preview", lambda guild_id: self.preview(event))

        for kind, session_name in RESULT_KINDS.items():
            slot = event.session(session_name)
            if slot is None or now < first_check(slot):
                continue
            state = await self.done(event, kind)
            if state is None:
                state = await self.look_for_results(now, event, kind, session_name, slot)
            if state == "ok":
                view = await ctx.db.cache_get(f"weekend:view:{event.year}:{event.round}:{kind}")
                await self.post_all(event, kind, lambda guild_id: self.results_post(event, session_name, view))
                if kind == "race":
                    await self.post_all(event, "predictions", lambda guild_id: self.predictions_post(event, guild_id))

        if await self.done(event, "race") == "ok" and now < race.start_utc + timedelta(days=4):
            await self.standings(now, event)

    async def preview(self, event):
        view = info.ScheduleView(event)
        try:
            latest = await info.schedule()
            if latest.event and (latest.event.year, latest.event.round) == (event.year, event.round):
                view = latest
        except SourceError:
            pass
        kwargs = {"embed": embeds.schedule(view)}
        if view.circuit_png:
            kwargs["file"] = common.png_file(view.circuit_png, "circuit.png")
        return kwargs

    async def look_for_results(self, now, event, kind, session_name, slot):
        key = (event.year, event.round, kind)
        if now < self.next_check.get(key, now):
            return None
        self.next_check[key] = now + CHECK_EVERY
        if now > first_check(slot) + GIVE_UP_AFTER:
            log.warning("no %s results for %s round %s after 24 hours; giving up", kind, event.year, event.round)
            await self.set_done(event, kind, "gave_up")
            return "gave_up"
        try:
            session = await fastf1_src.load(event.year, event.round, session_name, fresh=True)
        except SourceError as e:
            log.info("%s results not available yet: %s", kind, e)
            return None
        if not results_available(session.results):
            return None
        rows = info.quali_rows(session.results) if kind == "qualifying" else info.race_rows(session.results)
        await ctx.db.cache_set(f"weekend:view:{event.year}:{event.round}:{kind}",
                               [[r.position, r.name, r.team_id, r.value] for r in rows])
        if kind == "race":
            await self.after_race(event)
        await self.set_done(event, kind)
        return "ok"

    async def after_race(self, event):
        """Jobs that run once when a race result arrives. A failure in one doesn't block the post."""
        try:
            await info.fastest_lap(event)   # fills the /fl cache
        except Exception as e:
            log.warning("fastest lap for round %s not stored: %s", event.round, e)
        try:
            await game.score_round(event, *await game.official_result(event))
        except Exception as e:
            log.warning("predictions for round %s not scored: %s", event.round, e)

    async def results_post(self, event, session_name, stored):
        rows = tuple(info.ResultRow(*r) for r in stored or [])
        return {"embed": embeds.results(info.ResultView(event.year, event.name, rows), session_name)}

    async def predictions_post(self, event, guild_id):
        result = await game.actual(event)
        rows = [r for r in await game.for_event(guild_id, event) if r["points"] is not None]
        if not result or not rows:
            return None
        board = await game.leaderboard(guild_id, event.year)
        return {"embed": predictions_cog.results_embed(event, result, rows, board)}

    async def standings(self, now, event):
        """Jolpica updates some hours after a race; post once its standings include this round."""
        if await self.done(event, "standings"):
            await self.post_all(event, "standings", lambda guild_id: self._standings_kwargs(event))
            return
        key = (event.year, event.round, "standings")
        if now < self.next_check.get(key, now):
            return
        self.next_check[key] = now + timedelta(hours=1)
        try:
            drivers = await jolpica.driver_standings(event.year)
            if drivers["round"] != event.round:
                return
            constructors = await jolpica.constructor_standings(event.year)
            before_d = (await jolpica.driver_standings(event.year, event.round - 1))["rows"] if event.round > 1 else []
            before_c = (await jolpica.constructor_standings(event.year, event.round - 1))["rows"] \
                if event.round > 1 else []
        except SourceError as e:
            log.info("standings not available yet: %s", e)
            return
        embed = standings_embed(
            event,
            with_changes(drivers["rows"], before_d, lambda r: r["Driver"]["driverId"], 10),
            with_changes(constructors["rows"], before_c, lambda r: r["Constructor"]["constructorId"]))
        await ctx.db.cache_set(f"weekend:standings:{event.year}:{event.round}", embed.to_dict())
        await self.set_done(event, "standings")
        await self.post_all(event, "standings", lambda guild_id: self._standings_kwargs(event))

    async def _standings_kwargs(self, event):
        stored = await ctx.db.cache_get(f"weekend:standings:{event.year}:{event.round}")
        return {"embed": discord.Embed.from_dict(stored)} if stored else None

    # ------------------------------------------------------------ /remindme
    @app_commands.command(name="remindme", description="Get a DM before F1 sessions start")
    @app_commands.describe(sessions="Which sessions to be reminded about, or Off to stop",
                           lead="How long before the session to send the reminder")
    async def remindme(self, interaction: discord.Interaction,
                       sessions: Literal["All sessions", "Qualifying, sprint and race", "Race only", "Off"],
                       lead: Literal[15, 30, 60] = 30):
        text = await set_reminder("user", interaction.user.id, sessions, lead)
        await interaction.response.send_message(text, ephemeral=True)


async def set_reminder(kind: str, target_id: int, sessions: str, lead: int) -> str:
    if sessions == "Off":
        await ctx.db.q("DELETE FROM reminder_subscriptions WHERE kind=? AND target_id=? AND series=?",
                       kind, target_id, SERIES)
        return "Reminders are off."
    await ctx.db.q(
        "INSERT INTO reminder_subscriptions (kind, target_id, series, sessions, lead_minutes) VALUES (?,?,?,?,?) "
        "ON CONFLICT (kind, target_id, series) DO UPDATE SET sessions=excluded.sessions, "
        "lead_minutes=excluded.lead_minutes", kind, target_id, SERIES, SESSION_SETS[sessions], lead)
    return f"Reminders on: {sessions.lower()}, {lead} minutes before the start."


async def mark_weekend_seen(guild_id: int, now):
    """A server enabling weekend posts mid-weekend only gets kinds that become due afterwards."""
    events = await params.season(now.year)
    for event in events:
        if not event.race:
            continue
        kinds = [k for k in (*RESULT_KINDS, "standings") if await is_done(event, k)]
        if await is_done(event, "race") == "ok":
            kinds.append("predictions")
        if preview_time(event) <= now:
            kinds.append("preview")
        for kind in kinds:
            await ctx.db.q("INSERT OR IGNORE INTO weekend_posts VALUES (?,?,?,?,?,?)", guild_id, SERIES, event.year,
                           event.round, kind, int(time.time()))


async def setup(bot):
    await bot.add_cog(Watcher(bot))
