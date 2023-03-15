import discord
# import mediawiki
import requests
import json
import fastf1
import typing
import pandas as pd
from discord import app_commands
from discord.ext import commands
from lib.emojiid import team_emoji_ids
now = pd.Timestamp.now()

# check if given year and round number are valid
def checkYear(year,round):
    if not(year == None) and not(1950 <= year and year <= now.year):
        return "bad year"
    elif not(round == None) and not(round >= 1) and not(round < 25):
        return "bad round number"
    else:
        if (year == None and round == None):
            url =  "http://ergast.com/api/f1/constructors"
            return url
        elif (year == None):
            url = f"https://ergast.com/api/f1/{now.year}/{round}/constructors.json"
            return url
        elif (round == None):
            url =  f"https://ergast.com/api/f1/{year}/{1}/constructors.json"
            return url
        else: 
            url =  f"https://ergast.com/api/f1/{year}/{round}/constructors.json"
            return url

class constructor(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
    @commands.Cog.listener()
    async def on_ready(self):
        print('Constructors cog loaded')  
    @app_commands.command(name = 'team', description = 'Get constructor information')
    @app_commands.describe(year = "Constructor information")
    
    async def constructor(self, interaction: discord.Interaction, year: typing.Optional[int], round: typing.Optional[int]):  
        await interaction.response.defer()
        message_embed = discord.Embed(title=f"Constructor Information", description="").set_thumbnail(url='https://cdn.discordapp.com/attachments/884602392249770087/1059464532239581204/f1python128.png')
        message_embed.colour = discord.Colour.dark_red()
        url = checkYear(year,round)
        description_string = ''
        if ('bad' in url):
            description_string = "Please try again with a different " + url[url.index('bad')+3:]
        else:
            constructor_name, constructor_nationality, constructor_wikipedia = [], [], []
            
            try:
                constructor = requests.get(url)
                response = json.loads(constructor.content)
            except json.JSONDecodeError:
                if (year == None) or (1950 >= year and year >= now.year):
                    url = f"https://ergast.com/api/f1/current/constructors.json"
                    constructor = requests.get(url)
                    round = 1
                    response = json.loads(constructor.content)
                else:
                    url =  f"https://ergast.com/api/f1/{year}/{1}/constructors.json"
                    constructor = requests.get(url)
                    response = json.loads(constructor.content)
                
            amount_of_teams = int(response['MRData']['total'])
            if (amount_of_teams == 0):
                    description_string = f"No teams for this round."     
            else:
                year = int(response['MRData']['ConstructorTable']['season'])
                message_embed.title = f"{year} Round {round} constructor information" 
                
                for i in range(0, amount_of_teams):
                    constructor_data = (response['MRData']['ConstructorTable ']['Constructors'][0])
                    
                    try:
                        constructor_name.append(((str)(self.bot.get_emoji(team_emoji_ids[constructor_data['name']]))))
                    except:
                        constructor_name.append((constructor_data['name']))
                        
                    constructor_nationality.append(constructor_data['nationality'])
                    constructor_wikipedia.append(constructor_data['url'])
                    
                message_embed.add_field(name = "Name", value = '\n'.join(constructor_name),inline = True)
                message_embed.add_field(name = "Nationality", value = '\n'.join(constructor_nationality),inline = True)
                message_embed.add_field(name = "Wikipedia", value = '\n'.join(constructor_wikipedia),inline = True)
                
        # send final embed
        message_embed.description = description_string
        await interaction.followup.send(embed = message_embed)

async def setup(bot):
    await bot.add_cog(constructor(bot) # , guilds=[discord.Object(id=884602392249770084)]
                      )