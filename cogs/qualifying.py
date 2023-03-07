import discord
# import mediawiki
import requests
import json
import fastf1
import typing
import pandas as pd
from discord import app_commands
from discord.ext import commands
from emojiid import team_emoji_ids
now = pd.Timestamp.now()

class qualifying(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
    @commands.Cog.listener()
    async def on_ready(self):
        print('Qualifying cog loaded')  
    @app_commands.command(name='quali', description='Get qualifying results')
    @app_commands.describe(year = "Qualifying")
    
    async def qualifying(self, interaction: discord.Interaction, year: typing.Optional[int], round: typing.Optional[int]):
        await interaction.response.defer()
        
        # If user enters year without round, program crashes. Is bugged currently. Will fix later.
        if (year == None) or (year < 1994) or (year >= now.year) or (round < 0) or (round > 23):
            url = "https://ergast.com/api/f1/current/qualifying.json"
        elif (round >= 0 and round <= 23) and (year >=  1994 and year <= now):
            url = f"https://ergast.com/api/f1/{year}/{round}/qualifying.json"
        elif (year >=  1994 and year <= now) and (round == None):
            url = f"https://ergast.com/api/f1/{year}/1/qualifying.json"
            
        driver_names, driver_position, driver_times = [], [], []
        
        qualifying = requests.get(url)
        response = json.loads(qualifying.content)
        all_qualifying_times = (int)(response['MRData']['total'])
        
        # Handle when there are no qualifying sessions to be found (e.g. 1994, round 4). Not working well right now.
        if (all_qualifying_times == 0):
                print("No qualifying session for this round.")
                # setup(bot)
                message_embed = discord.Embed(title=f"No available times for this round.", description="").set_thumbnail(url='https://cdn.discordapp.com/attachments/884602392249770087/1059464532239581204/f1python128.png')
                exit()
                
        year = (response['MRData']['RaceTable']['Races'][0]['season']) 
        raceName = (response['MRData']['RaceTable']['Races'][0]['raceName'])  
        message_embed = discord.Embed(title=f"{year} {raceName} Qualifying Results", description="").set_thumbnail(url='https://cdn.discordapp.com/attachments/884602392249770087/1059464532239581204/f1python128.png')
        message_embed.colour = discord.Colour.dark_red()
        
        for i in range(0, all_qualifying_times):
            
            qualifying_results = (response['MRData']['RaceTable']['Races'][0]['QualifyingResults'][i])
            driver_data = (response['MRData']['RaceTable']['Races'][0]['QualifyingResults'][i]['Driver'])
            constructor_data = (response['MRData']['RaceTable']['Races'][0]['QualifyingResults'][i]['Constructor'])
            
            try:
                # Emojis still seem to print out fine in most cases, so set this to 34 for now.
                if (all_qualifying_times <= 34):
                    driver_names.append(((str)(self.bot.get_emoji(team_emoji_ids[constructor_data['name']]))) + ' ' + (driver_data['givenName']) + ' ' +  driver_data['familyName'])
                else: 
                    driver_names.append((driver_data['givenName']) + ' ' +  driver_data['familyName'])
            except:
                driver_names.append((driver_data['givenName']) + ' ' + driver_data['familyName'])
                
            driver_position.append(qualifying_results['position'])
            if 'Q3' in qualifying_results:
                driver_times.append("Q3: " + qualifying_results['Q3'])
            elif 'Q2' in qualifying_results:
                driver_times.append("Q2: " + qualifying_results['Q2'])
            elif 'Q1' in qualifying_results:
                driver_times.append("Q1: " + qualifying_results['Q1'])     
            else: 
                driver_times.append("No time set.")
            
        message_embed.add_field(name="Position", value='\n'.join(driver_position),inline=True)
        message_embed.add_field(name="Driver", value='\n'.join(driver_names),inline=True)
        message_embed.add_field(name="Times", value='\n'.join(driver_times),inline=True)
        # send final embed
        await interaction.followup.send(embed=message_embed)

async def setup(bot):
    await bot.add_cog(qualifying(bot) # , guilds=[discord.Object(id=884602392249770084)]
                      )