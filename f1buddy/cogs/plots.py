import hashlib
import logging
from typing import Literal, Optional

import discord
from discord import app_commands
from discord.ext import commands

from .. import ctx, util
from ..data import plots
from ..errors import SourceError
from ..render import embeds
from ..sources import gemini
from . import common

log = logging.getLogger(__name__)
ROUND = "Round name or number; defaults to the latest"
YEAR = "Season (2018 onwards); defaults to the latest"
DRIVER = "Driver code or name, e.g. VER"


async def send_plot(interaction, png: bytes, meta: dict, extra: str = ""):
    embed = embeds.make(meta["title"], util.clamp((meta.get("description") or "") + extra, 4096), meta.get("footer"))
    embed, file = embeds.with_image(embed, png)
    await interaction.followup.send(embed=embed, file=file)


async def ai_text(png: bytes, meta: dict, requested: bool) -> str:
    """The 'AI Analysis' block for a telemetry reply, or a short reason it is missing."""
    if not requested:
        return ""
    if not gemini.available():
        return "\n\nAI analysis isn't configured on this bot."
    key = "ai:" + hashlib.sha1(png).hexdigest()
    text = await ctx.db.cache_get(key)
    if text is None:
        try:
            text = await gemini.analyse_telemetry(png, meta["description"].replace("\n", ", "))
        except SourceError as e:
            log.warning("AI analysis failed: %s", e)
            return "\n\nAI analysis is unavailable right now."
        await ctx.db.cache_set(key, text)
    return f"\n\n**AI Analysis**\n{text}"


class Plots(commands.Cog):
    category = "Plots"

    @app_commands.command(name="laptimes", description="Compare laptimes of two drivers in a race (2018 onwards)")
    @app_commands.describe(driver1=DRIVER, driver2=DRIVER, round=ROUND, year=YEAR)
    @app_commands.autocomplete(driver1=common.driver_autocomplete, driver2=common.driver_autocomplete,
                               round=common.round_autocomplete)
    async def laptimes(self, interaction: discord.Interaction, driver1: str, driver2: str,
                       round: Optional[str] = None, year: Optional[int] = None):
        await interaction.response.defer()
        await send_plot(interaction, *await plots.laptimes(driver1, driver2, round, year))

    @app_commands.command(name="positions", description="See driver position changes over the race")
    @app_commands.describe(round=ROUND, year=YEAR)
    @app_commands.autocomplete(round=common.round_autocomplete)
    async def positions(self, interaction: discord.Interaction, round: Optional[str] = None,
                        year: Optional[int] = None):
        await interaction.response.defer()
        await send_plot(interaction, *await plots.positions(round, year))

    @app_commands.command(name="strategy", description="See tire strategies for the race")
    @app_commands.describe(round=ROUND, year=YEAR)
    @app_commands.autocomplete(round=common.round_autocomplete)
    async def strategy(self, interaction: discord.Interaction, round: Optional[str] = None,
                       year: Optional[int] = None):
        await interaction.response.defer()
        await send_plot(interaction, *await plots.strategy(round, year))

    @app_commands.command(name="qualigap", description="See each driver's qualifying gap to pole")
    @app_commands.describe(round=ROUND, year=YEAR)
    @app_commands.autocomplete(round=common.round_autocomplete)
    async def qualigap(self, interaction: discord.Interaction, round: Optional[str] = None,
                       year: Optional[int] = None):
        await interaction.response.defer()
        await send_plot(interaction, *await plots.qualigap(round, year))

    @app_commands.command(name="consistency", description="Plot driver laptime consistency")
    @app_commands.describe(driver=DRIVER, round=ROUND, year=YEAR)
    @app_commands.autocomplete(driver=common.driver_autocomplete, round=common.round_autocomplete)
    async def consistency(self, interaction: discord.Interaction, driver: str, round: Optional[str] = None,
                          year: Optional[int] = None):
        await interaction.response.defer()
        await send_plot(interaction, *await plots.consistency(driver, round, year))

    @app_commands.command(
        name="telemetry",
        description="Compare telemetry between 2 drivers on a specific lap, leave blank for respective fastest laps")
    @app_commands.describe(driver1=DRIVER, driver2="Second driver; leave blank for a single-driver plot",
                           round=ROUND, session="Session; defaults to the race", year=YEAR,
                           lap="Lap number; defaults to each driver's fastest lap",
                           ai_analysis="Add an AI race-engineer analysis of the plot")
    @app_commands.autocomplete(driver1=common.driver_autocomplete, driver2=common.driver_autocomplete,
                               round=common.round_autocomplete)
    @app_commands.choices(session=common.SESSION_CHOICES)
    async def telemetry(self, interaction: discord.Interaction, driver1: str, driver2: Optional[str] = None,
                        round: Optional[str] = None, session: Optional[str] = None, year: Optional[int] = None,
                        lap: Optional[int] = None, ai_analysis: bool = False):
        await interaction.response.defer()
        png, meta = await plots.telemetry(driver1, driver2, round, session, year, lap)
        await send_plot(interaction, png, meta, await ai_text(png, meta, ai_analysis))

    @app_commands.command(name="trackdominance",
                          description="See track dominance between drivers on their personal fastest laps")
    @app_commands.describe(driver1=DRIVER, driver2=DRIVER, round=ROUND,
                           session="Session; defaults to qualifying", year=YEAR)
    @app_commands.autocomplete(driver1=common.driver_autocomplete, driver2=common.driver_autocomplete,
                               round=common.round_autocomplete)
    @app_commands.choices(session=common.SESSION_CHOICES)
    async def trackdominance(self, interaction: discord.Interaction, driver1: str, driver2: str,
                             round: Optional[str] = None, session: Optional[str] = None,
                             year: Optional[int] = None):
        await interaction.response.defer()
        await send_plot(interaction, *await plots.trackdominance(driver1, driver2, round, session, year))

    @app_commands.command(
        name="avgpos",
        description="See average finish position for driver for race/qualifying throughout the year")
    @app_commands.describe(category="Average per driver or per team", session="Race or qualifying positions",
                           exclude_dnfs="Which retirements to leave out (races only); default None",
                           year="Season (1950 onwards; qualifying from 1994); defaults to the latest")
    async def avgpos(self, interaction: discord.Interaction, category: Literal["Drivers", "Teams"],
                     session: Literal["Race", "Qualifying"],
                     exclude_dnfs: Literal["None", "Mechanical only", "All"] = "None",
                     year: Optional[int] = None):
        await interaction.response.defer()
        exclude = {"None": "none", "Mechanical only": "mechanical", "All": "all"}[exclude_dnfs]
        await send_plot(interaction, *await plots.avgpos(category, session, exclude, year))

    @app_commands.command(name="h2h",
                          description="See head to head stats of specific drivers or teammate pairings.")
    @app_commands.describe(session="Race or qualifying results",
                           exclude_dnfs="Skip rounds where either teammate retired (races only)",
                           year="Season (1950 onwards; qualifying from 1994); defaults to the latest")
    async def h2h(self, interaction: discord.Interaction, session: Literal["Race", "Qualifying"],
                  exclude_dnfs: bool = False, year: Optional[int] = None):
        await interaction.response.defer()
        await send_plot(interaction, *await plots.h2h(session, exclude_dnfs, year))


async def setup(bot):
    await bot.add_cog(Plots())
