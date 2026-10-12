from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands

from ..data import info
from ..render import embeds
from . import common


class Info(commands.Cog):
    category = "Information"

    @app_commands.command(name="schedule", description="Next race weekend: sessions, local times, circuit and weather")
    async def schedule(self, interaction: discord.Interaction):
        await interaction.response.defer()
        view = await info.schedule()
        kwargs = {"embed": embeds.schedule(view)}
        if view.event and view.circuit_png:
            kwargs["file"] = common.png_file(view.circuit_png, "circuit.png")
        await interaction.followup.send(**kwargs)

    @app_commands.command(name="wdc", description="Get driver standings")
    @app_commands.describe(year="Season (1950 onwards); defaults to the latest")
    async def wdc(self, interaction: discord.Interaction, year: Optional[int] = None):
        await interaction.response.defer()
        await interaction.followup.send(embed=embeds.wdc(await info.driver_standings(year)))

    @app_commands.command(name="wcc", description="Get constructor standings")
    @app_commands.describe(year="Season (1958 onwards); defaults to the latest")
    async def wcc(self, interaction: discord.Interaction, year: Optional[int] = None):
        await interaction.response.defer()
        await interaction.followup.send(embed=embeds.wcc(await info.constructor_standings(year)))

    @app_commands.command(name="constructors", description="Get constructor information")
    @app_commands.describe(year="Season (1950 onwards); defaults to the latest")
    async def constructors(self, interaction: discord.Interaction, year: Optional[int] = None):
        await interaction.response.defer()
        await interaction.followup.send(embed=embeds.constructors(*await info.constructors(year)))

    @app_commands.command(name="driver", description="Get driver info")
    @app_commands.describe(driver="Driver name; pick from the list or type a full name")
    async def driver(self, interaction: discord.Interaction, driver: str):
        await interaction.response.defer()
        egg = embeds.easter_egg(driver)
        if egg:
            await interaction.followup.send(embed=egg)
            return
        await interaction.followup.send(embed=embeds.driver(await info.driver_profile(driver)))

    @driver.autocomplete("driver")
    async def _driver_ac(self, interaction: discord.Interaction, current: str):
        return common._choices(await info.driver_autocomplete(current))

    @app_commands.command(name="results",
                          description="Get results of a specific race or the latest by leaving all options blank")
    @app_commands.describe(round="Round name or number (Australia or 3)", year="Season (1950 onwards)")
    @app_commands.autocomplete(round=common.round_autocomplete)
    async def results(self, interaction: discord.Interaction, round: Optional[str] = None,
                      year: Optional[int] = None):
        await interaction.response.defer()
        await interaction.followup.send(embed=embeds.results(await info.race_results(year, round)))

    @app_commands.command(name="qualifying",
                          description="Get results of a qualifying session or the latest by leaving all options blank")
    @app_commands.describe(round="Round name or number (Australia or 3)", year="Season (1994 onwards)")
    @app_commands.autocomplete(round=common.round_autocomplete)
    async def qualifying(self, interaction: discord.Interaction, round: Optional[str] = None,
                         year: Optional[int] = None):
        await interaction.response.defer()
        view = await info.qualifying_results(year, round)
        await interaction.followup.send(embed=embeds.results(view, "Qualifying"))

    @app_commands.command(name="fl", description="Get fastest lap")
    @app_commands.describe(round="Round name or number; leave blank for the whole season",
                           year="Season (2018 onwards)")
    @app_commands.autocomplete(round=common.round_autocomplete)
    async def fl(self, interaction: discord.Interaction, round: Optional[str] = None,
                 year: Optional[int] = None):
        await interaction.response.defer()
        year, rows = await info.fastest_laps(year, round)
        await interaction.followup.send(embeds=embeds.fastest_laps(year, rows))


async def setup(bot):
    await bot.add_cog(Info())
