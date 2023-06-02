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
now = pd.Timestamp.now()

# check if given year and round number are valid
def checkYear(year,round):
    if not(year == None) and not(1950 <= year and year <= now.year):
        return "bad year"
    elif not(round == None) and not(round >= 1) and not(round < 25):
        return "bad round number"
    else:
        if (year == None and round == None):
            url =  f"http://ergast.com/api/f1/{now.year}/constructors.json"
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

class Constructor(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
    @commands.Cog.listener()
    async def on_ready(self):
        print('Constructors cog loaded')  
    @app_commands.command(name = 'team', description = 'Get constructor information')
    @app_commands.describe(year = "Constructor information")
    
    async def Constructor(self, interaction: discord.Interaction, year: typing.Optional[int], round: typing.Optional[int]):  
        await interaction.response.defer()
        message_embed = discord.Embed(title=f"Constructor Information", description="").set_thumbnail(url='https://cdn.discordapp.com/attachments/884602392249770087/1059464532239581204/f1python128.png')
        message_embed.colour = colors.default
        url = checkYear(year,round)
        # print(url)
        description_string = ''
        nationality_dict = nation_dictionary()

        # with open('lib/nation.csv') as csv_file:
        #     csv_read = csv.reader(csv_file, delimiter=',')


        if ('bad' in url):
            description_string = "Please try again with a different " + url[url.index('bad')+3:]
        else:
            constructor_name, constructor_nationality, constructor_wikipedia, constructor_championships = [], [], [], []
            
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
                if (round == 0):
                    round = int(response['MRData']['ConstructorTable']['round'])
                    message_embed.title = f"{year} Round {round} Constructor Information" 
                else:
                    message_embed.title = f"{year} Constructor Information" 
                    
                for i in range(amount_of_teams):
                    constructor_data = (response['MRData']['ConstructorTable']['Constructors'][i])
                        
                    try:
                        constructor_name.append((str)(self.bot.get_emoji(team_emoji_ids[constructor_data['name']]))+' ' + constructor_data['name'])
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
                    string += f"[{constructor_name[j]}]({constructor_wikipedia[j]})\n"
                
                message_embed.add_field(name="Team", value=string, inline=True)
                message_embed.add_field(name = "Nationality", value = '\n'.join(constructor_nationality),inline = True)
                message_embed.add_field(name = "Championships", value = '\n'.join(constructor_championships),inline = True)
                nation_dictionary()

                
        # send final embed
        message_embed.description = description_string
        await interaction.followup.send(embed = message_embed)

async def setup(bot):
    await bot.add_cog(Constructor(bot) # , guilds=[discord.Object(id=884602392249770084)]
                      )
