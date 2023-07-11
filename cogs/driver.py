import asyncio
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
from lib.colors import colors

WIKI_REQUEST = 'http://en.wikipedia.org/w/api.php?action=query&prop=pageimages&format=json&piprop=original&titles='
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

def get_driver(driver):
    # setup embed
    message_embed = discord.Embed(title="temp_driver_title", description="")
    message_embed.set_author(name='f1buddy',icon_url='https://raw.githubusercontent.com/F1-Buddy/f1buddy-python/main/botPics/f1pythonpfp.png')
    
    message_embed.colour = colors.default
    if 'anurag' in driver:
        message_embed.set_image(url='https://avatars.githubusercontent.com/u/100985214?v=4')
        message_embed.title = 'friend anurag'
        return message_embed
    
        
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
    # img_url = unidecode(driver).title()
    wiki_image = get_wiki_image(driver)

    # iterate through driver data to find a match
    index = -1
    for i in range(len(driver_data)):
        normalized_name = unidecode(driver_data[i]['name']).casefold()
        if normalized_name == normalized_input:
            index = i
            break
    if index == -1:
        message_embed.set_image(url='https://media.tenor.com/lxJgp-a8MrgAAAAd/laeppa-vika-half-life-alyx.gif')
        message_embed.set_thumbnail(url='https://cdn.discordapp.com/attachments/884602392249770087/1059464532239581204/f1python128.png')
        message_embed.title = "Driver \"" +driver+ "\" not found!"
        message_embed.description = "Try a driver's full name!"
        return message_embed
        # message_embed.timestamp = datetime.datetime.now()
        # message_embed.set_footer(text ='\u200b',icon_url="https://cdn.discordapp.com/attachments/884602392249770087/1059464532239581204/f1python128.png")
    else:
        if wiki_image != 0:
            message_embed.set_image(url=wiki_image)
        message_embed.title = driver_data[index]['name']
        message_embed.url = wikipedia.WikipediaPage(title = wikipedia.search(driver, results = 1)[0]).url
        # message_embed.add_field(name = "Nationality", inline = True, image=f"https:{driver_data[index]['nationality']}")
        message_embed.description += "**:calendar_spiral: Seasons Completed:** "+str(driver_data[index]['seasons_completed'])
        message_embed.description += "\n**:trophy: Championships:** "+str(driver_data[index]['championships'])
        message_embed.description += "\n**:checkered_flag: Entries:** "+str(driver_data[index]['entries'])
        message_embed.description += "\n**:race_car: Starts:** "+str(driver_data[index]['starts'])
        message_embed.description += "\n**:stopwatch: Poles:** "+str(driver_data[index]['poles'])
        message_embed.description += "\n**:first_place: Wins:** "+str(driver_data[index]['wins'])
        message_embed.description += "\n**:medal: Podiums:** "+str(driver_data[index]['podiums'])
        message_embed.description += "\n**:rocket: Fastest Laps:** "+str(driver_data[index]['fastest_laps'])
        message_embed.description += "\n**:chart_with_upwards_trend: Points:** "+str(driver_data[index]['points'])
        message_embed.set_thumbnail(url=f"https:{driver_data[index]['nationality']}")
        # message_embed.add_field(name = "Seasons Completed "+str(driver_data[index]['seasons_completed']),value=" ",inline = True)
        # message_embed.add_field(name = ":trophy: Championships "+str(driver_data[index]['championships']),value=" ",inline = True)
        # message_embed.add_field(name = ":checkered_flag: Entries "+str(driver_data[index]['entries']),value=" ",inline = True)
        # message_embed.add_field(name = ":checkered_flag: Starts "+str(driver_data[index]['starts']),value=" ",inline = True)
        # message_embed.add_field(name = ":stopwatch: Poles "+str(driver_data[index]['poles']),value=" ",inline = True)
        # message_embed.add_field(name = ":first_place: Wins "+str(driver_data[index]['wins']),value=" ",inline = True)
        # message_embed.add_field(name = ":medal: Podiums "+str(driver_data[index]['podiums']),value=" ",inline = True)
        # message_embed.add_field(name = ":purple_square: Fastest Laps "+str(driver_data[index]['fastest_laps']),value=" ",inline = True)
        # message_embed.add_field(name = ":chart_with_upwards_trend: Points "+str(driver_data[index]['points']),value=" ",inline = True)
        # message_embed.timestamp = datetime.datetime.now()
        # message_embed.set_footer(text ='\u200b',icon_url="https://cdn.discordapp.com/attachments/884602392249770087/1059464532239581204/f1python128.png")
        # print(message_embed)
        return message_embed
        

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
        loop = asyncio.get_running_loop()
        result_embed = await loop.run_in_executor(None, get_driver, driver)
        # send final embed
        await interaction.followup.send(embed= result_embed)

async def setup(bot):
    await bot.add_cog(Driver(bot)
    # , guilds=[discord.Object(id=884602392249770084)]
    )
