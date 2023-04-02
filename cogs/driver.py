import discord
# import wikipedia as wk
import mediawiki
import requests
import json
# import fastf1
# import pandas as pd
from discord import app_commands
from discord.ext import commands
from lib.drivernames import driver_names
import country_converter as coco
from pyquery import PyQuery as pq
# from geopy.geocoders import Nominatim
# from timezonefinder import TimezoneFinder
# import country_converter as coco

stat_map = {
    'Starts':'starts',
    'Career Points': 'careerpoints',
    'Wins':'wins',
    'Podiums':'podiums',
    'Poles':'poles',
    'Fastest Laps':'fastestlaps',    
}

class Driver(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        print('Driver cog loaded')

    @app_commands.command(name='driver', description='Get driver info')
    @app_commands.describe(driver = "Driver full name")
    # @app_commands.describe(driver="Driver")
    # @app_commands.choices(driver = driver_list)
    async def driver(self, interaction: discord.Interaction, driver:str):
        await interaction.response.defer()

        # driver list

        # setup embed
        message_embed = discord.Embed(title="temp_driver_title", description="")
        message_embed.set_thumbnail(url='https://cdn.discordapp.com/attachments/884602392249770087/1059464532239581204/f1python128.png')
        message_embed.colour = discord.Colour.dark_red()
        description_string = ''
        
        # get wikipedia article
        wk = mediawiki.MediaWiki()
        driver_article = wk.page(title=driver,auto_suggest=True)
        # emoji = ":flag_" + (coco.convert(names='', to='ISO2')).lower()+":"

        # get driver image
        article_url = f"https://en.wikipedia.org/w/api.php?action=query&prop=pageimages&format=json&piprop=original&titles={(str)(driver_article.title)}"
        article_json = requests.get(article_url)
        response = json.loads(article_json.content)
        driver_image_url = (response['query']['pages'][driver_article.pageid]['original']['source'])
        
        driver_table = pq(url='https://en.wikipedia.org/wiki/List_of_Formula_One_drivers')('table.wikitable.sortable')

        # Extract the column names from the first row of the <thead> section
        # heading_names = []
        # thead_row = pq(driver_table)('thead tr')
        # headings = [pq(cell).text() for cell in pq(thead_row)('th')]
        # heading_names.append(headings)


        # Extract the data from each row of the <tbody> section
        rows = []
        for row in pq(driver_table)('tbody tr'):
            # Extract the data for each column in the row
            columns = [pq(cell).text() for cell in pq(row)('td')]
            rows.append(columns)

        # Print the column headings and data rows
        # for heading in heading_names:
        #     print(heading)
        # for row in rows:
        #     print(row)

        driver_row = None
        for row in rows[1:]:
            driver_name, driver_nationality, driver_years_active, wins, podiums, poles, fastest_laps, points, entries, championships, constructors_championships = row
            # print(rows[1])
            print("Driver name:", driver_name)
            print("Driver nationality:", driver_nationality)
            print("Years active:", driver_years_active)
            print("Wins:", wins)
            print("Podiums:", podiums)
            print("Poles:", poles)
            print("Fastest laps:", fastest_laps)
            print("Points:", points)
            print("Entries:", entries)
            print("Championships:", championships)
            print("Constructors championships:", constructors_championships)
            # if row[0] == driver:
            #     driver_row = row
            #     break

        if driver_row is not None:
            # extract stats from the row
            stats = dict(zip(stat_map.values(), driver_row[2:]))
            description_string = '\n'.join([f"{k.capitalize()}: **{v}**" for k, v in stats.items()])


        # get other driver info like stats
        driver_full_name = driver_article.title
        driver_info = json.loads(requests.get(f"https://ergast.com/api/f1/drivers/{(str)(driver_full_name[driver_full_name.index(' ')+1:])}.json").content)
        try:
            driver_code = driver_names[driver_full_name]
        except:
            driver_code = driver_info["MRData"]["DriverTable"]["Drivers"][0]["code"]

        # get F1Stats (wins,points,starts, etc.)
        for x in stat_map:
            stat_url = f"https://en.wikipedia.org/w/api.php?action=expandtemplates&format=json&text={{{{F1stat|{driver_code}|{stat_map[x]}}}}}&prop=wikitext"
            # print(stat_url)
            stat_json = json.loads(requests.get(stat_url).content)
            if len((y := stat_json['expandtemplates']['wikitext'])) > 0:
                description_string += f"{x}: **{y}**\n"
                # description_string += x+": **"+ y + "**\n"
            else:
                print(driver_article.html)
                break

        message_embed.set_image(url=driver_image_url)
        message_embed.title = driver_full_name
        message_embed.description = description_string

        # send final embed
        await interaction.followup.send(embed=message_embed)

async def setup(bot):
    await bot.add_cog(Driver(bot)
    # , guilds=[discord.Object(id=884602392249770084)]
    )