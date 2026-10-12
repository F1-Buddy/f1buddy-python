"""/setup: per-server settings. Every subcommand needs the Manage Server permission."""
from typing import Literal, Optional

import discord
from discord import app_commands
from discord.ext import commands

from .. import ctx, util
from ..errors import UserError
from . import fia as fia_cog
from . import watcher

Channel = discord.TextChannel   # announcement channels are text channels too


def missing_permissions(channel, me) -> str:
    """A warning if the bot can't post what it needs to in a channel, else an empty string."""
    perms = channel.permissions_for(me)
    missing = [name for name, ok in (("Send Messages", perms.send_messages), ("Attach Files", perms.attach_files),
                                     ("Embed Links", perms.embed_links)) if not ok]
    return f"\n⚠️ I'm missing these permissions there: {', '.join(missing)}." if missing else ""


def guild_of(interaction) -> int:
    if interaction.guild_id is None:
        raise UserError("This command only works in a server.")
    return interaction.guild_id


@app_commands.default_permissions(manage_guild=True)
@app_commands.guild_only()
class Setup(commands.GroupCog, group_name="setup", group_description="Configure f1buddy for this server"):
    category = "Setup"

    @app_commands.command(name="fia", description="Choose the channel for automatic FIA document posts")
    @app_commands.describe(channel="Channel to post new FIA documents in; leave blank to turn them off")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def fia(self, interaction: discord.Interaction, channel: Optional[Channel] = None):
        guild_id = guild_of(interaction)
        await fia_cog.set_channel(guild_id, channel.id if channel else None)
        if channel is None:
            text = "Automatic FIA document posts are off."
        else:
            text = (f"New FIA documents will be posted in {channel.mention}."
                    + missing_permissions(channel, interaction.guild.me))
        await interaction.response.send_message(text, ephemeral=True)

    @app_commands.command(name="reminders", description="Post a reminder in a channel before sessions start")
    @app_commands.describe(channel="Channel for reminders; leave blank to turn them off",
                           role="Role to mention with each reminder",
                           sessions="Which sessions to remind about",
                           lead="How long before the session to post")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def reminders(self, interaction: discord.Interaction, channel: Optional[Channel] = None,
                        role: Optional[discord.Role] = None,
                        sessions: Literal["All sessions", "Qualifying, sprint and race",
                                          "Race only"] = "Qualifying, sprint and race",
                        lead: Literal[15, 30, 60] = 30):
        guild_id = guild_of(interaction)
        await ctx.db.set_setting(guild_id, "reminder_channel_id", channel.id if channel else None)
        await ctx.db.set_setting(guild_id, "reminder_role_id", role.id if role and channel else None)
        if channel is None:
            await watcher.set_reminder("guild", guild_id, "Off", lead)
            text = "Session reminders are off for this server."
        else:
            await watcher.set_reminder("guild", guild_id, sessions, lead)
            text = (f"Reminders will be posted in {channel.mention}: {sessions.lower()}, {lead} minutes before."
                    + (f" Mentioning {role.mention}." if role else "")
                    + missing_permissions(channel, interaction.guild.me))
        await interaction.response.send_message(text, ephemeral=True,
                                                allowed_mentions=discord.AllowedMentions.none())

    @app_commands.command(name="weekend", description="Post previews, results and standings automatically")
    @app_commands.describe(channel="Channel for race-weekend posts; leave blank to turn them off")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def weekend(self, interaction: discord.Interaction, channel: Optional[Channel] = None):
        guild_id = guild_of(interaction)
        await ctx.db.set_setting(guild_id, "weekend_channel_id", channel.id if channel else None)
        if channel is None:
            text = "Automatic weekend posts are off."
        else:
            await watcher.mark_weekend_seen(guild_id, util.now())
            text = (f"Weekend previews, results and standings will be posted in {channel.mention}."
                    + missing_permissions(channel, interaction.guild.me))
        await interaction.response.send_message(text, ephemeral=True)


async def setup(bot):
    await bot.add_cog(Setup())
