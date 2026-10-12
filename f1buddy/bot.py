import logging

import discord
from discord import app_commands
from discord.ext import commands

from . import ctx
from .db import Database
from .errors import SourceError, UserError
from .render import embeds
from .sources import fastf1_src

log = logging.getLogger(__name__)
COGS = ["info", "plots", "fia", "watcher", "predictions", "live", "misc"]


def error_message(error: Exception) -> str:
    """What the user is told for a given failure. Never a traceback."""
    original = getattr(error, "original", error)
    if isinstance(original, UserError):
        return str(original)
    if isinstance(original, SourceError):
        log.warning("source failure: %s", original)
        return f"Couldn't reach {original.source}. Try again in a few minutes."
    if isinstance(error, app_commands.MissingPermissions):
        return "You need the Manage Server permission to do that."
    if isinstance(error, app_commands.NoPrivateMessage):
        return "This command only works in a server."
    log.error("unhandled command error", exc_info=original)
    return "Something went wrong. It's been logged."


async def on_app_command_error(interaction: discord.Interaction, error: Exception):
    embed = embeds.error(error_message(error))
    try:
        if interaction.response.is_done():
            # a deferred reply is public; drop it so the error can be ephemeral
            try:
                await interaction.delete_original_response()
            except discord.HTTPException:
                pass
            await interaction.followup.send(embed=embed, ephemeral=True)
        else:
            await interaction.response.send_message(embed=embed, ephemeral=True)
    except discord.HTTPException:
        log.exception("could not deliver error message")


class F1Buddy(commands.Bot):
    def __init__(self, config):
        intents = discord.Intents.default()
        intents.message_content = True  # only for the f1$sync prefix command
        super().__init__(command_prefix="f1$", intents=intents, help_command=None)
        self.config = config

    async def setup_hook(self):
        config = self.config
        config.data_dir.mkdir(parents=True, exist_ok=True)
        (config.data_dir / "plots").mkdir(exist_ok=True)
        ctx.config = config
        ctx.db = Database(config.data_dir / "f1buddy.db")
        fastf1_src.init(config.data_dir)
        self.tree.on_error = on_app_command_error

        for name in COGS:
            try:
                await self.load_extension(f"f1buddy.cogs.{name}")
            except Exception:
                log.exception("cog %s failed to load; continuing without it", name)

        try:
            for emoji in await self.fetch_application_emojis():
                embeds.EMOJIS[emoji.name] = str(emoji)
        except discord.HTTPException:
            log.warning("could not fetch application emojis; continuing without them")

    async def on_ready(self):
        embeds.AVATAR_URL = self.user.display_avatar.url
        log.info("logged in as %s in %d servers", self.user, len(self.guilds))

    async def alert(self, message: str):
        """Operational alert to the owner's channel, if one is configured."""
        log.warning("ALERT: %s", message)
        channel = self.get_channel(self.config.alert_channel_id) if self.config.alert_channel_id else None
        if channel:
            try:
                await channel.send(message)
            except discord.HTTPException:
                log.exception("could not send alert")
