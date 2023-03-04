import discord
# import wikipedia as wk
import mediawiki
import requests
import json
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
        
        # get wikipedia article
        wk = mediawiki.MediaWiki()
        driver_article = wk.page(title=driver,auto_suggest=True)

        # get driver image
        article_url = "https://en.wikipedia.org/w/api.php?action=query&prop=pageimages&format=json&piprop=original&titles=" + (str)(driver_article.title)
        article_json = requests.get(article_url)
        response = json.loads(article_json.content)
        driver_image_url = (response['query']['pages'][driver_article.pageid]['original']['source'])



        # page_html = driver_article.html
        # image_index = driver_article.html.index("class=\"infobox-image\">")
        # page_html = page_html[image_index:image_index+61]
        # print(driver_article.html.index("class=\"infobox-image\">"))
        # print(page_html)

        message_embed.set_image(url=driver_image_url)
        message_embed.title = driver_article.title
        


        # send final embed
        await interaction.followup.send(embed=message_embed)


async def setup(bot):
    await bot.add_cog(Driver(bot)
    # , guilds=[discord.Object(id=884602392249770084)]
    )