import discord
# import wikipedia as wk
import mediawiki as wk
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

    @commands.Cog.listener()
    async def on_ready(self):
        print('Driver cog loaded')

    driver_list = [
        
    ]

    @app_commands.command(name='driver', description='Get driver info')
    @app_commands.describe(driver = "Driver name")
    # @app_commands.describe(driver="Driver")
    # @app_commands.choices(driver = driver_list)
    async def driver(self, interaction: discord.Interaction, driver:str):
        await interaction.response.defer()

        # driver list

        # setup embed
        message_embed = discord.Embed(title="temp_driver_title", description="")
        message_embed.set_thumbnail(url='https://cdn.discordapp.com/attachments/884602392249770087/1059464532239581204/f1python128.png')
        
        # 
        # print wikipedias suggested article based on user input
        driver_article = wk.MediaWiki.page(title=driver)
        print(driver_article.title)
        # returning nothing
        print(driver_article.sections)

        # message_embed.set_image(url=driver_article.images[0])


        # send final embed
        await interaction.followup.send(embed=message_embed)


async def setup(bot):
    await bot.add_cog(Driver(bot)
    # , guilds=[discord.Object(id=884602392249770084)]
    )