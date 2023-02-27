import discord
# import fastf1
# import pandas as pd
from discord import app_commands
from discord.ext import commands
# from geopy.geocoders import Nominatim
# from timezonefinder import TimezoneFinder
# import country_converter as coco

class Driver(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # print('hi')
    @commands.Cog.listener()
    async def on_ready(self):
        print('Driver cog loaded')

    @app_commands.command(name='driver', description='get driver info')
    async def driver(self, interaction: discord.Interaction):
        await interaction.response.defer()
        message_embed = discord.Embed(title="temp_driver_title", description="")
        message_embed.set_thumbnail(url='https://cdn.discordapp.com/attachments/884602392249770087/1059464532239581204/f1python128.png')


async def setup(bot):
    await bot.add_cog(Driver(bot)
    # , guilds=[discord.Object(id=884602392249770084)]
    )