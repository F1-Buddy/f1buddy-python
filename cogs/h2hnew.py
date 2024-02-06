import discord
import asyncio
import fastf1
import os
import traceback
import typing
from discord import app_commands
from discord.ext import commands
from matplotlib import pyplot as plt
from matplotlib.offsetbox import AnnotationBbox, OffsetImage
from numpy import mean
from lib.f1font import regular_font, bold_font
import matplotlib.patches as mpatches
import matplotlib
# from matplotlib.ticker import (MultipleLocator)
# matplotlib.use('agg')
# from lib.colors import colors
# import country_converter as coco
import lib.emojiid as emoji
import repeated.common as cm
import repeated.embed as em
import pandas as pd
import fastf1.plotting as f1plt


# get current time
now = pd.Timestamp.now()

fastf1.Cache.enable_cache('cache/')

class session_type:
    def __init__(self, name, value):
        self.name = name
        self.value = value

def get_data(year, session_type):
    # the code for this is kinda bad and complicated so imma leave comments for when i forget what any of this does
    team_list = {}
    driver_country = {}
    # outstring = ''
    schedule = fastf1.get_event_schedule(year=year,include_testing=False)
    for c in range(min(schedule.index), max(schedule.index)+1):
    # for c in range(min(schedule.index),min(schedule.index)+5):
        session = fastf1.get_session(year, schedule.loc[c,'RoundNumber'], session_type.value)
        session.load(laps=False, telemetry=False, weather=False, messages=False)
        results = session.results
        # print(results)
        # for driver in results.index:
        #     country_code = results.loc[driver,'CountryCode']
        #     if not (country_code == ''):
        #         driver_country.update({results.loc[driver,'Abbreviation']:country_code})
        
        # for each race, reset the boolean
        # boolean is used to prevent same driver being updated twice in the same race since it iterates through every driver
        # EX: if VER finished ahead of PER, first VER is updated to +1, boolean is set to true, 
        # that way when loop gets to PER it doesnt add +1 to VER again since boolean is true
        # until the next race when they can be updated again
        for i in team_list.keys():
            for c in team_list.get(i).keys():
                team_list.get(i).get(c).update({'round_updated':False})
        
        for i in results['TeamName']:
            team_results = results.loc[lambda df: df['TeamName'] == i]
            # if (i == "Ferrari"):
            #     print(team_results)
            #     print(team_results.loc[team_results.index[1],'ClassifiedPosition'])
            drivers = []
            for j in team_results.index:
                drivers.append(team_results.loc[j,'Abbreviation'])
            drivers = sorted(drivers)
            pairing = ''.join(drivers)
            # create dictionary entries if not existing
            # dictionary format:
            # teamName:
            #   driverPairing:
            #       driver: #ofRacesFinishedAheadofTeammate
            #       otherDriver: #ofRacesFinishedAheadofTeammate
            if (team_list.get(i) is None):
                team_list.update({i:{}})
            if (team_list.get(i).get(pairing) is None):
                team_list.get(i).update({pairing:{}})
            
            # print(pairing)
            # print(team_list)
            curr_abbr = team_results.loc[team_results.index[0],'Abbreviation']
            
            # figure out which races to ignore
            both_drivers_finished = True
            dnf = ['R','D','E','W','F','N']
            for driver in team_results.index:
                if ((team_results.loc[driver,'ClassifiedPosition']) in dnf) | (not ((team_results.loc[driver,'Status'] == 'Finished') | ('+' in team_results.loc[driver,'Status']))):
                    # outstring += (f'{pairing}: Skipping {session}\nReason: {team_results.loc[driver,'Abbreviation']} did {team_results.loc[driver,'ClassifiedPosition']}\n')
                    both_drivers_finished = False
            
            # if include this race, then update the driver pairing's h2h "points"
            if (both_drivers_finished):
                if (team_list.get(i).get(pairing).get(curr_abbr) is None):
                    team_list.get(i).get(pairing).update({curr_abbr:0})
                if (team_list.get(i).get(pairing).get('round_updated') is None):
                    team_list.get(i).get(pairing).update({'round_updated':False})
                if not team_list.get(i).get(pairing).get('round_updated'):
                    curr_value = team_list.get(i).get(pairing).get(curr_abbr)
                    # print(f'curr_value = {curr_value}')
                    team_list.get(i).get(pairing).update({curr_abbr:curr_value+1})
                    team_list.get(i).get(pairing).update({'round_updated':True})
    return team_list,driver_country #, outstring

def print_data(data):
    for team in data.keys():
        print(team)
        for pairing in data.get(team).keys():
            print(f'    {pairing}:')
            for driver in data.get(team).get(pairing):
                if not (driver == 'round_updated'):
                    print(f'        {driver}: {data.get(team).get(pairing).get(driver)}')

def h2h_embed(self,data,year,session_type):
    title = f"Teammate {session_type.name} Head to Head {year}"
    description = ''
    print(title)
    try:
        for team in data.keys():
            for pairing in data.get(team).keys():
                drivers = []
                for driver in data.get(team).get(pairing):
                    if not (driver == 'round_updated'):
                        drivers.append(driver)
                description += f' {drivers[0]} {data.get(team).get(pairing).get(drivers[0])} {self.bot.get_emoji(emoji.team_emoji_ids.get(team))} {data.get(team).get(pairing).get(drivers[1])} {drivers[1]}\n'
    except:
        traceback.print_exc()
    print(description)
    return title, description
    

def get_embed(self, year, session_type):
    if (year is None):
        year = now.year
        if cm.currently_offseason()[0]:
            year = year - 1
    
    data,countries = get_data(year, session_type)
    # for country in countries.values():
    #     print(f":flag_{coco.convert(names=country,to="ISO2",not_found=None).lower()}:")
    print_data(data)
    return h2h_embed(self, data,year,session_type)
    # print(out)
    
# sessiontype = session_type('Race','r')
# main(2023, sessiontype)
class h2hnew(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
    @commands.Cog.listener()
    async def on_ready(self):
        print('H2H V2 cog loaded')  
    @app_commands.command(name='h2h', description='See head to head stats of specific drivers or teammate pairings.')
    @app_commands.describe(year = "Year")
    @app_commands.describe(session_type='Choose between Qualifying or Race')
    @app_commands.choices(session_type=[app_commands.Choice(name="Race", value="Race"), 
                                 app_commands.Choice(name="Qualifying", value="Qualifying"),])
    
    async def h2hnew(self, interaction: discord.Interaction, year: typing.Optional[int], session_type: app_commands.Choice[str]):  
        await interaction.response.defer()
        loop = asyncio.get_running_loop()

        title, description = await loop.run_in_executor(None, get_embed, self, year, session_type)
        # results_embed.set_author(name='f1buddy',icon_url='https://raw.githubusercontent.com/F1-Buddy/f1buddy-python/main/botPics/f1pythonpfp.png')
        # send embed
        await interaction.followup.send(content=f"{title}\n{description}")
        # await interaction.followup.send(video_url)
        loop.close()

async def setup(bot):
    await bot.add_cog(h2hnew(bot) # , guilds=[discord.Object(id=884602392249770084)]
                      )