"""/help, /lightsout and the f1$sync prefix command."""
import asyncio
import random
import time
from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands

from .. import util
from ..render import embeds

CATEGORIES = ["Information", "Plots", "FIA documents", "Reminders", "Predictions", "Live", "Setup", "Other"]
HELP_DIR = util.ASSETS / "help"
LINKS = ("If you are having any issues or want to provide feedback, please open a new issue on "
         "[GitHub](https://github.com/F1-Buddy/f1buddy-python/issues)\n"
         "If you need additional assistance, join the [f1buddy support server](https://discord.gg/Qx3gqWrpzJ)")
CAR = "🏎️"


def leaf_commands(tree) -> list[app_commands.Command]:
    """Every runnable slash command, with subcommands flattened ('predict pole')."""
    return [c for c in tree.walk_commands() if isinstance(c, app_commands.Command)]


def help_overview(tree) -> discord.Embed:
    groups = {}
    for cmd in leaf_commands(tree):
        category = getattr(cmd.binding, "category", "Other")
        groups.setdefault(category, []).append(f"`/{cmd.qualified_name}` — {cmd.description}")
    embed = embeds.make("f1buddy Help", "Use `/help command:` followed by a command name for details.\n\n" + LINKS)
    for category in CATEGORIES:
        if category in groups:
            embed.add_field(name=category, value=util.clamp("\n".join(sorted(groups[category])), 1024), inline=False)
    return embed


def help_detail(tree, name: str):
    """(embed, screenshot path or None) for one command, or (None, None) if it doesn't exist."""
    name = name.lower().strip().lstrip("/")
    cmd = next((c for c in leaf_commands(tree) if c.qualified_name == name), None)
    if cmd is None:
        return None, None
    lines = [cmd.description, ""]
    for p in cmd.parameters:
        need = "required" if p.required else "optional"
        choices = f" One of: {', '.join(c.name for c in p.choices)}." if p.choices else ""
        lines.append(f"`{p.display_name}` ({need}) — {p.description}{choices}")
    shot = HELP_DIR / f"{name.replace(' ', '_')}.png"
    return embeds.make(f"f1buddy Help - {name}", "\n".join(lines)), shot if shot.exists() else None


class Misc(commands.Cog):
    category = "Information"

    def __init__(self, bot):
        self.bot = bot

    # ------------------------------------------------------------------ help
    @app_commands.command(name="help", description="List the commands, or explain one")
    @app_commands.describe(command="Command to explain")
    async def help(self, interaction: discord.Interaction, command: Optional[str] = None):
        tree = interaction.client.tree
        if not command:
            await interaction.response.send_message(embed=help_overview(tree))
            return
        embed, shot = help_detail(tree, command)
        if embed is None:
            embed = embeds.make("f1buddy Help", f"Command '{command}' not recognized. Use /help to see all commands.")
            shot = HELP_DIR / "laeppa-vika-half-life-alyx.gif"
        if shot and shot.exists():
            embed.set_image(url=f"attachment://{shot.name}")
            await interaction.response.send_message(embed=embed, file=discord.File(shot, filename=shot.name))
        else:
            await interaction.response.send_message(embed=embed)

    @help.autocomplete("command")
    async def _help_ac(self, interaction: discord.Interaction, current: str):
        names = sorted(c.qualified_name for c in leaf_commands(interaction.client.tree))
        return [app_commands.Choice(name=n, value=n) for n in names if current.lower() in n][:25]

    # ------------------------------------------------------------- lightsout
    @app_commands.command(name="lightsout", description="Wait for the lights and react the fastest!")
    async def lightsout(self, interaction: discord.Interaction):
        await interaction.response.defer()
        await self.play(interaction)

    async def play(self, interaction, *, delay=None, step=1.0, timeout=30.0):
        """The game itself. `delay`, `step` and `timeout` are parameters so tests run in milliseconds."""
        delay = random.randrange(0, 600) / 100.0 if delay is None else delay

        def grid(red):
            row = " ".join([":red_circle:"] * red + [":black_circle:"] * (5 - red))
            return f"{row}\n{row}"

        intro = "Wait for the lights and react the fastest!\n\n{}\n\n\n\n{}"
        embed = embeds.make("Lights out!", intro.format(grid(0), ":red_square:      :race_car:"))
        message = await interaction.followup.send(embed=embed, wait=True)

        jump_starts = []
        lights_out_at = None
        winner = asyncio.get_running_loop().create_future()

        async def on_reaction_add(reaction, user):
            if reaction.message.id != message.id or user.bot or str(reaction.emoji) != CAR:
                return
            if lights_out_at is None:
                if user not in jump_starts:
                    jump_starts.append(user)
            elif user not in jump_starts and not winner.done():
                winner.set_result((user, time.monotonic() - lights_out_at))

        self.bot.add_listener(on_reaction_add, "on_reaction_add")
        try:
            await message.add_reaction(CAR)
            for red in range(1, 6):
                await asyncio.sleep(step)
                embed.description = intro.format(grid(red), ":red_square:      :race_car:")
                await message.edit(embed=embed)
            await asyncio.sleep(delay)
            embed.description = intro.format(grid(0), ":green_square:      :race_car::dash:")
            await message.edit(embed=embed)
            lights_out_at = time.monotonic()

            jumped = lambda: f"\nJump start: {', '.join(u.mention for u in jump_starts)}" if jump_starts else ""
            try:
                user, reaction_time = await asyncio.wait_for(winner, timeout)
            except asyncio.TimeoutError:
                embed.title = "No one got away"
                embed.description = f"{grid(0)}{jumped()}"
            else:
                embed.title = "And away we go!"
                embed.description = (f"{user.mention} got away the fastest!\n\n{grid(0)}\n\n\n\n"
                                     f":checkered_flag:      :race_car:{jumped()}")
                embed.set_footer(text=f"Lights held for {delay} seconds · reacted in {reaction_time:.3f} s")
            await message.edit(embed=embed)
        finally:
            self.bot.remove_listener(on_reaction_add, "on_reaction_add")
        return embed

    # ------------------------------------------------------------------ sync
    @commands.command(name="sync")
    async def sync(self, ctx: commands.Context):
        if ctx.author.id not in self.bot.config.admin_ids:
            await ctx.send(f"{ctx.author.display_name} is not a bot admin! Can't sync :(")
            return
        await self.bot.change_presence(activity=discord.Activity(
            type=discord.ActivityType.listening, name=f"V10s | /help | {len(self.bot.guilds)} servers"))
        synced = await self.bot.tree.sync()
        await ctx.send(f"{ctx.author.mention} synced {len(synced)} commands")


async def setup(bot):
    await bot.add_cog(Misc(bot))
