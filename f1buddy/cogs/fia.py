"""/fiadoc and the automatic FIA document poster (spec 04)."""
import asyncio
import hashlib
import logging
import time
from datetime import datetime, timedelta, timezone
from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands, tasks

from .. import ctx, util
from ..data import params
from ..errors import ParseError, SourceError, UserError
from ..render import embeds
from ..render import fia as fia_render
from ..sources import fia
from . import common

log = logging.getLogger(__name__)
MAX_PAGES = 20
STALE_AFTER = 600   # /fiadoc refreshes the list if the last good poll is older than this


def poll_interval(now: datetime, events) -> timedelta:
    """5 minutes from Thursday 00:00 UTC of a race week to the Monday 12:00 UTC after it; 30 otherwise."""
    for event in events:
        if not event.race:
            continue
        race_day = event.race.start_utc.replace(hour=0, minute=0, second=0, microsecond=0)
        thursday = race_day - timedelta(days=(race_day.weekday() - 3) % 7)
        monday = race_day + timedelta(days=(7 - race_day.weekday()) % 7 or 7, hours=12)
        if thursday <= now <= monday:
            return timedelta(minutes=5)
    return timedelta(minutes=30)


def doc_embed(row, title=None) -> discord.Embed:
    when = util.ts(datetime.fromtimestamp(row["published_at"], timezone.utc)) if row["published_at"] else ""
    lines = [row["title"]] if title else []
    lines += [x for x in (row["event"], when) if x]
    embed = embeds.make(title or row["title"], "\n".join(lines), "FIA document")
    embed.url = row["url"]
    return embed


async def mark_all_posted(guild_id: int):
    """A server only ever receives documents that appear after it turned the feature on."""
    await ctx.db.q("INSERT OR IGNORE INTO fia_posts SELECT url, ?, ? FROM fia_documents", guild_id, int(time.time()))


async def set_channel(guild_id: int, channel_id: int | None):
    await ctx.db.set_setting(guild_id, "fia_channel_id", channel_id)
    if channel_id:
        await mark_all_posted(guild_id)


class Fia(commands.Cog):
    category = "FIA documents"

    def __init__(self, bot):
        self.bot = bot
        self.failures = 0           # consecutive failed polls
        self.down_since = None
        self.alerted_at = None
        self.last_run = None
        self.doc_failures = {}      # url -> failed download/render attempts
        self.guild_failures = {}    # guild id -> consecutive failed sends

    async def cog_load(self):
        self.loop.start()

    async def cog_unload(self):
        self.loop.cancel()

    # ------------------------------------------------------------- polling
    @tasks.loop(minutes=5)
    async def loop(self):
        now = util.now()
        try:
            interval = poll_interval(now, await params.season(now.year))
        except Exception:
            interval = timedelta(minutes=30)
        if self.last_run and now - self.last_run < interval - timedelta(seconds=30):
            return
        self.last_run = now
        try:
            await self.poll_once(now)
        except Exception:
            log.exception("FIA poll failed")   # never stops the loop, never retries early

    @loop.before_loop
    async def _wait(self):
        await self.bot.wait_until_ready()

    async def adopt_config_channel(self):
        """FIA_CHANNEL_ID in the environment sets that channel's server, as if /setup fia had been run."""
        channel_id = ctx.config.fia_channel_id
        channel = self.bot.get_channel(channel_id) if channel_id else None
        if channel is None:
            return
        row = await ctx.db.one("SELECT fia_channel_id FROM guild_settings WHERE guild_id = ?", channel.guild.id)
        if row is None or row["fia_channel_id"] != channel_id:
            await set_channel(channel.guild.id, channel_id)

    async def poll_once(self, now=None) -> bool:
        """Fetch the listing, record new documents, post what each server hasn't had. True on success."""
        now = now or util.now()
        try:
            docs = fia.parse_listing(await fia.fetch_listing())
        except SourceError as e:
            await self._poll_failed(e, now)
            return False
        if self.alerted_at is not None:
            await self.bot.alert("FIA documents: working again.")
        self.failures, self.down_since, self.alerted_at = 0, None, None
        await ctx.db.cache_set("fia:last_success", now.timestamp())

        await self.adopt_config_channel()
        first_run = (await ctx.db.one("SELECT COUNT(*) AS n FROM fia_documents"))["n"] == 0
        for doc in reversed(docs):   # oldest first, so row order follows age
            await ctx.db.q("INSERT OR IGNORE INTO fia_documents (url, title, event, published_at, first_seen_at) "
                           "VALUES (?, ?, ?, ?, ?)", doc.url, doc.title, doc.event,
                           int(doc.published_at.timestamp()) if doc.published_at else None, int(now.timestamp()))
        if first_run:   # never post a backlog
            for guild in await ctx.db.guilds_with("fia_channel_id"):
                await mark_all_posted(guild["guild_id"])
            return True
        await self.post_pending()
        return True

    async def _poll_failed(self, error, now):
        self.failures += 1
        self.down_since = self.down_since or now
        log.warning("FIA poll failed (%d in a row): %s", self.failures, error)
        if not (isinstance(error, ParseError) or self.failures >= 6):
            return
        if self.alerted_at and now - self.alerted_at < timedelta(hours=24):
            return
        self.alerted_at = now
        if isinstance(error, ParseError):
            await self.bot.alert("FIA documents: the page no longer parses. See specs/04-fia-documents.md.")
        else:
            await self.bot.alert(f"FIA documents: unreachable since {util.ts(self.down_since)}.")

    async def post_pending(self):
        pending = await ctx.db.q(
            "SELECT d.*, g.guild_id, g.fia_channel_id FROM fia_documents d "
            "JOIN guild_settings g ON g.fia_channel_id IS NOT NULL "
            "LEFT JOIN fia_posts p ON p.url = d.url AND p.guild_id = g.guild_id "
            "WHERE p.url IS NULL ORDER BY COALESCE(d.published_at, d.first_seen_at), d.rowid")
        for row in pending:
            try:
                pages, total = await self.pages(row)
            except SourceError as e:
                self.doc_failures[row["url"]] = self.doc_failures.get(row["url"], 0) + 1
                log.warning("FIA document %s failed: %s", row["url"], e)
                if self.doc_failures[row["url"]] < 3:
                    continue
                pages, total = [], 0   # one bad PDF must not block the queue: post it as a link
            await self.post(row, pages, total)

    async def post(self, row, pages, total):
        guild_id = row["guild_id"]
        channel = self.bot.get_channel(row["fia_channel_id"])
        try:
            if channel is None:
                raise LookupError("channel not found")
            note = f"Showing {len(pages)} of {total} pages. Full document: {row['url']}" if total > len(pages) else None
            message = await common.send_pages(channel.send, doc_embed(row), pages, note)
        except (discord.HTTPException, LookupError) as e:
            self.guild_failures[guild_id] = self.guild_failures.get(guild_id, 0) + 1
            log.warning("FIA post to server %s failed: %s", guild_id, e)
            if self.guild_failures[guild_id] >= 3:
                await ctx.db.set_setting(guild_id, "fia_channel_id", None)
                self.guild_failures.pop(guild_id)
            return
        self.guild_failures.pop(guild_id, None)
        await ctx.db.q("INSERT OR IGNORE INTO fia_posts VALUES (?, ?, ?)", row["url"], guild_id, int(time.time()))
        if getattr(channel, "type", None) == discord.ChannelType.news:
            try:
                await message.publish()
            except discord.HTTPException:
                log.warning("could not publish FIA post in %s", channel)

    async def pages(self, row) -> tuple[list[bytes], int]:
        """Rendered pages for a document, from the shared on-disk cache when present."""
        folder = ctx.config.data_dir / "fia" / hashlib.sha1(row["url"].encode()).hexdigest()
        files = sorted(folder.glob("*.png")) if folder.exists() else []
        if files and row["page_count"]:
            return [f.read_bytes() for f in files], row["page_count"]
        pdf = await fia.fetch_pdf(row["url"])
        pages, total = await asyncio.to_thread(fia_render.render_pages, pdf, MAX_PAGES)
        folder.mkdir(parents=True, exist_ok=True)
        for i, png in enumerate(pages, start=1):
            (folder / f"{i:03}.png").write_bytes(png)   # zero-padded: listing order is page order
        await ctx.db.q("UPDATE fia_documents SET page_count = ? WHERE url = ?", total, row["url"])
        return pages, total

    # ------------------------------------------------------------- command
    async def newest(self, limit=25):
        return await ctx.db.q("SELECT * FROM fia_documents ORDER BY COALESCE(published_at, 0) DESC, rowid DESC "
                              "LIMIT ?", limit)

    @app_commands.command(name="fiadoc", description="Get latest FIA Document")
    @app_commands.describe(doc="Go back X documents (0 is the newest)")
    async def fiadoc(self, interaction: discord.Interaction, doc: Optional[int] = None):
        await interaction.response.defer()
        index = doc or 0
        note = None
        last = await ctx.db.cache_get("fia:last_success")
        if last is None or util.now().timestamp() - last > STALE_AFTER:
            if not await self.poll_once():
                note = "The FIA site couldn't be reached; this may not be the latest."
        rows = await self.newest(index + 1) if index >= 0 else []
        if not rows and note:
            raise SourceError("the FIA website", "no stored documents and the site is unreachable")
        if index < 0 or index >= len(rows):
            raise UserError("Document doesn't exist!")
        row = rows[index]
        try:
            pages, total = await self.pages(row)
        except SourceError:
            pages, total, note = [], 0, "The document couldn't be loaded from the FIA site; use the link above."
        embed = doc_embed(row, "Latest FIA Document" if index == 0 else None)
        if total > len(pages):
            note = " ".join(x for x in (note, f"Showing {len(pages)} of {total} pages. Full document: {row['url']}")
                            if x)
        await common.send_pages(interaction.followup.send, embed, pages, note)

    @fiadoc.autocomplete("doc")
    async def _doc_ac(self, interaction: discord.Interaction, current: str):
        rows = await self.newest()
        labels = [(f"{r['title']} — {r['event']}" if r["event"] else r["title"], i) for i, r in enumerate(rows)]
        return [app_commands.Choice(name=label[:100], value=i) for label, i in labels
                if util.fold(str(current)) in util.fold(label)][:25]


async def setup(bot):
    await bot.add_cog(Fia(bot))
