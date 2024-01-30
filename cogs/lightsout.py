import asyncio
import datetime
import time
import discord
import typing
import pandas as pd
# from fastf1.ergast import Ergast
# import fastf1
from discord import app_commands
from discord.ext import commands
# from lib.emojiid import team_emoji_ids
# from lib.colors import colors
import repeated.embed as em


async def lights(interaction):
    print(interaction)
        
class lightsoutgame(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        print('lightsoutgame cog loaded')

    @app_commands.command(name='lightsoutgame', description='lightsoutgame')
    async def schedule(self, interaction: discord.Interaction):
        # defer response
        await interaction.response.defer()     
        await interaction.followup.send(content="hi")
        await asyncio.sleep(1)
        await interaction.edit_original_response(content="hhh")
        loop = asyncio.get_running_loop()
        # run query and build embed
        loop.run_in_executor(None, lights, interaction)
        loop.close()
        
        
async def setup(bot):
    await bot.add_cog(lightsoutgame(bot))