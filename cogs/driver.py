import datetime
import re
import discord
import pandas as pd
import wikipedia
import requests
import json
from unidecode import unidecode
from bs4 import BeautifulSoup
from discord import app_commands
from discord.ext import commands
from lib.drivernames import driver_names
import country_converter as coco

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
            
    async def driver(self, interaction: discord.Interaction, driver:str):
        await interaction.response.defer()
        WIKI_REQUEST = 'http://en.wikipedia.org/w/api.php?action=query&prop=pageimages&format=json&piprop=original&titles='

        # setup embed
        message_embed = discord.Embed(title="temp_driver_title", description="")
        
        message_embed.colour = discord.Colour.dark_red()
        
        def get_wiki_image(search_term):
            try:
                result = wikipedia.search(search_term, results = 1)
                wikipedia.set_lang('en')
                wkpage = wikipedia.WikipediaPage(title = result[0])
                title = wkpage.title
                response  = requests.get(WIKI_REQUEST+title)
                json_data = json.loads(response.text)
                img_link = list(json_data['query']['pages'].values())[0]['original']['source']
                return img_link        
            except:
                return 0
            
        url = 'https://en.wikipedia.org/wiki/List_of_Formula_One_drivers'
        response = requests.get(url)
        soup = BeautifulSoup(response.text, "lxml")
        table = soup.find('table', {'class': 'wikitable sortable'})
        
        def parse_driver_name(name):
            return name.strip().replace("~", "").replace("*", "").replace("^", "")

        def parse_championships(championships):
            champ_val = championships.split('<')[0].strip()[0]
            return int(champ_val) if champ_val.isdigit() else 0
        
        def parse_brackets(text):
            return re.sub(r'\[.*?\]', '', text)
        
        driver_data = []
        
        for row in table.find_all('tr')[1:]:
            columns = row.find_all('td')
            flags = row.find('img', {'class': 'thumbborder'})
            if flags:
                nationality = flags['src']
            if columns:
                driver_dict = {
                    'name': parse_driver_name(columns[0].text.strip()),
                    'nationality': nationality,
                    'seasons_completed': columns[2].text.strip(),
                    'championships': parse_championships(columns[3].text.strip()),
                    'entries': parse_brackets(columns[4].text.strip()),
                    'starts': parse_brackets(columns[5].text.strip()),
                    'poles': parse_brackets(columns[6].text.strip()),
                    'wins': parse_brackets(columns[7].text.strip()),
                    'podiums': parse_brackets(columns[8].text.strip()),
                    'fastest_laps': parse_brackets(columns[9].text.strip()),
                    'points': parse_brackets(columns[10].text.strip())
                }
                driver_data.append(driver_dict)
                
        normalized_input = unidecode(driver).casefold()
        img_url = unidecode(driver).title()
        wiki_image = get_wiki_image(driver)

        # iterate through driver data to find a match
        index = -1
        for i in range(len(driver_data)):
            normalized_name = unidecode(driver_data[i]['name']).casefold()
            if normalized_name == normalized_input:
                index = i
                break
        if index == -1:
            message_embed.set_thumbnail(url='https://cdn.discordapp.com/attachments/884602392249770087/1059464532239581204/f1python128.png')
            message_embed.title = "Driver \"" +driver+ "\" not found!"
            message_embed.description = "Try a driver's full name"
            message_embed.timestamp = datetime.datetime.now()
            message_embed.set_footer(text ='\u200b',icon_url="https://cdn.discordapp.com/attachments/884602392249770087/1059464532239581204/f1python128.png")
        else:
            if wiki_image != 0:
                message_embed.set_image(url=wiki_image)
            message_embed.title = driver_data[index]['name']
            message_embed.url = wikipedia.WikipediaPage(title = wikipedia.search(driver, results = 1)[0]).url
            # message_embed.add_field(name = "Nationality", inline = True, image=f"https:{driver_data[index]['nationality']}")
            message_embed.set_thumbnail(url=f"https:{driver_data[index]['nationality']}")
            message_embed.add_field(name = "Seasons Completed", value = (driver_data[index]['seasons_completed']),inline = True)
            message_embed.add_field(name = "Championships", value = (driver_data[index]['championships']),inline = True)
            message_embed.add_field(name = "Entries", value = (driver_data[index]['entries']),inline = True)
            message_embed.add_field(name = "Starts", value = (driver_data[index]['starts']),inline = True)
            message_embed.add_field(name = "Poles", value = (driver_data[index]['poles']),inline = True)
            message_embed.add_field(name = "Wins", value = (driver_data[index]['wins']),inline = True)
            message_embed.add_field(name = "Podiums", value = (driver_data[index]['podiums']),inline = True)
            message_embed.add_field(name = "Fastest Laps", value = (driver_data[index]['fastest_laps']),inline = True)
            message_embed.add_field(name = "Points", value = (driver_data[index]['points']),inline = True)
            message_embed.timestamp = datetime.datetime.now()
            message_embed.set_footer(text ='\u200b',icon_url="https://cdn.discordapp.com/attachments/884602392249770087/1059464532239581204/f1python128.png")

        # send final embed
        await interaction.followup.send(embed=message_embed)

async def setup(bot):
    await bot.add_cog(Driver(bot)
    # , guilds=[discord.Object(id=884602392249770084)]
    )