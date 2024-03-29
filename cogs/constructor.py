import asyncio
import traceback
import discord
import requests
import json
import typing
import pandas as pd
from discord import app_commands
from discord.ext import commands
from lib.emojiid import team_emoji_ids
from lib.emojiid import nation_dictionary
from lib.championship import constructor_championship
from lib.colors import colors
import country_converter as coco
import repeated.common as cm
import repeated.embed as em

# this shit sucks
# fix later
def check_year(year,round):
    now = pd.Timestamp.now()
    if not(year is None) and not(1950 <= year and year <= now.year):
        return "bad year"
    # lol 
    elif not(round == None) and not(round >= 1) and not(round < 25):
        return "bad round number"
    else:
        if (year is None and round == None):
            url =  f"http://ergast.com/api/f1/{now.year}/constructors.json"
            return url
        elif (year is None):
            url = f"https://ergast.com/api/f1/{now.year}/{round}/constructors.json"
            return url
        elif (round == None):
            url =  f"https://ergast.com/api/f1/{year}/{1}/constructors.json"
            return url
        else: 
            url =  f"https://ergast.com/api/f1/{year}/{round}/constructors.json"
            return url



def get_constructor_info(self, year):
    
    
    now = pd.Timestamp.now()
    if year is None:
        year = now.year
        if (cm.currently_offseason()[0]) or (cm.latest_completed_index(now.year) == 0):
            year -= 1
    url = f"http://ergast.com/api/f1/{year}/constructors.json"
    # print(url)
    description_string = ''
    nationality_dict = nation_dictionary()

    # with open('lib/nation.csv') as csv_file:
    #     csv_read = csv.reader(csv_file, delimiter=',')


    constructor_name, constructor_nationality, constructor_wikipedia, constructor_championships = [], [], [], []
        
    try:
        constructor = requests.get(url)
        response = json.loads(constructor.content)
    except json.JSONDecodeError:
        if (year is None) or (1950 >= year and year >= now.year):
            url = f"https://ergast.com/api/f1/current/constructors.json"
            constructor = requests.get(url)
            # round = 1
            response = json.loads(constructor.content)
        else:
            url =  f"https://ergast.com/api/f1/{year}/{1}/constructors.json"
            constructor = requests.get(url)
            response = json.loads(constructor.content)
    try:    
        amount_of_teams = int(response['MRData']['total'])
        if (amount_of_teams == 0):
                description_string = f"No teams for this round."     
        else:
            year = int(response['MRData']['ConstructorTable']['season'])
            # if (round == 0 or round == None):
            #     title = f"{year} Constructor Information" 
            # elif (round > 0):
            #     round = int(response['MRData']['ConstructorTable']['round'])
            #     title = f"{year} Round {round} Constructor Information" 
            # else:
            title = f"{year} Constructor Information" 
                
            for i in range(amount_of_teams):
                constructor_data = (response['MRData']['ConstructorTable']['Constructors'][i])
                    
                try:
                    if amount_of_teams <= 11:
                        constructor_name.append((str)(self.bot.get_emoji(team_emoji_ids[constructor_data['name']]))+' ' + constructor_data['name'])
                    elif year == 2010 or year == 2011:
                        constructor_name.append((constructor_data['name']))
                    else:
                        constructor_name.append((constructor_data['name']))
                except:
                    constructor_name.append((constructor_data['name']))
                    
                if constructor_data['name'] in constructor_championship:
                    constructor_championships.append(constructor_championship[constructor_data['name']])
                else:
                    constructor_championships.append("0")
                emoji = ":flag_" + \
                    (coco.convert(
                    names=nationality_dict[constructor_data['nationality']], to='ISO2')).lower()+":"
                constructor_nationality.append(emoji + " " + constructor_data['nationality'])
                constructor_wikipedia.append(constructor_data['url'])
            
            string = ""
            for j in range(amount_of_teams):
                try:
                    team_name = f"{constructor_name[j][0:constructor_name[j].index('>')+1]}[{constructor_name[j][constructor_name[j].index('>')+1:]}]({constructor_wikipedia[j]})"
                    string += team_name + "\n"
                except:
                    team_name = f"[{constructor_name[j]}]({constructor_wikipedia[j]})"
                    string += team_name + "\n"
            
            # print(string)
            dc_embed = em.Embed(title=title, description=description_string, )
            dc_embed.embed.add_field(name="Team", value=string, inline=True)
            dc_embed.embed.add_field(name = "Nationality", value = '\n'.join(constructor_nationality),inline = True)
            dc_embed.embed.add_field(name = "Championships", value = '\n'.join(constructor_championships),inline = True)
            dc_embed.embed.description = description_string
            # nation_dictionary()
            return dc_embed
    except:
        return em.ErrorEmbed(error_message=traceback.format_exc())
        

class constructor(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
    @commands.Cog.listener()
    async def on_ready(self):
        print('Constructors cog loaded')  
    @app_commands.command(name = 'constructors', description = 'Get constructor information')
    @app_commands.describe(year = "Constructor information")
    
    async def constructor(self, interaction: discord.Interaction, year: typing.Optional[int]):  
        await interaction.response.defer()
        loop = asyncio.get_running_loop()
        try:
            # run query and build embed
            constructor_embed = await loop.run_in_executor(None, get_constructor_info, self, year)
            # constructor_embed.set_author(name='f1buddy', icon_url='https://raw.githubusercontent.com/F1-Buddy/f1buddy-python/main/botPics/f1pythonpfp.png')
            # send embed
            await interaction.followup.send(embed=constructor_embed.embed)
        except Exception as e:
            await interaction.followup.send(f"An error occurred: {e}")
        loop.close()

async def setup(bot):
    await bot.add_cog(constructor(bot) # , guilds=[discord.Object(id=884602392249770084)]
                      )