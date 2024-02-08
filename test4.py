import math
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
import matplotlib.patheffects as pe
import matplotlib
import matplotlib.image as mpim
from PIL import Image
import urllib.request
import io
import numpy as np
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
    color_list = {}
    check_list = {}
    driver_country = {}
    outstring = ''
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
        for i in check_list.keys():
            check_list.update({i:False})
        
        for i in results['TeamId']:
            team_results = results.loc[lambda df: df['TeamId'] == i]
            # testing
            # if (i == "Ferrari"):
            #     print(team_results)
            # print(team_results[['Abbreviation','ClassifiedPosition','Status','TeamColor','TeamId']])
                
            # dictionary format:
            # teamName:
            #   driverPairing:
            #       driver: #ofRacesFinishedAheadofTeammate
            #       otherDriver: #ofRacesFinishedAheadofTeammate
            if (team_list.get(i) is None):
                team_list.update({i:{}})
                color_list.update({i:team_results.loc[min(team_results.index),'TeamColor']})

            drivers = []
            for j in team_results.index:
                drivers.append(team_results.loc[j,'Abbreviation'])
            drivers = sorted(drivers)
            pairing = ''.join(drivers)

            if (team_list.get(i).get(pairing) is None):
                team_list.get(i).update({pairing:{}})

            for abbreviation in team_results['Abbreviation']:
                if team_list.get(i).get(pairing).get(abbreviation) is None:
                    team_list.get(i).get(pairing).update({abbreviation:0})

            curr_abbr = team_results.loc[team_results.index[0],'Abbreviation']
            
            # figure out which races to ignore
            both_drivers_finished = True
            dnf = ['D','E','W','F','N']
            for driver in team_results.index:
                if ((team_results.loc[driver,'ClassifiedPosition']) in dnf) | (not ((team_results.loc[driver,'Status'] == 'Finished') | ('+' in team_results.loc[driver,'Status']))):
                    # for testing
                    # outstring += (f'{pairing}: Skipping {session}\nReason: {team_results.loc[driver,'Abbreviation']} did ({team_results.loc[driver,'ClassifiedPosition']},{team_results.loc[driver,'Status']})\n')
                    both_drivers_finished = False
            
            # if (team_list.get(i).get(pairing).get(curr_abbr) is None):
            #     team_list.get(i).get(pairing).update({curr_abbr:0})
            if (check_list.get(i) is None):
                check_list.update({i:False})
            if not check_list.get(i):
                curr_value = team_list.get(i).get(pairing).get(curr_abbr)
                # if include this race, then update the driver pairing's h2h "points"
                if (both_drivers_finished):
                    team_list.get(i).get(pairing).update({curr_abbr:curr_value+1})
                    check_list.update({i:True})
            else:
                curr_value = team_list.get(i).get(pairing).get(curr_abbr)
                team_list.get(i).get(pairing).update({curr_abbr:curr_value})
    return team_list,color_list #, outstring

def print_data(data):
    for team in data.keys():
        print(team)
        for pairing in data.get(team).keys():
            print(f'    {pairing}:')
            for driver in data.get(team).get(pairing):
                print(f'        {driver}: {data.get(team).get(pairing).get(driver)}')

def h2h_embed(self,data,year,session_type):
    title = f"Teammate {session_type.name} Head to Head {year}"
    description = ''
    for team in data.keys():
        description += f'{self.bot.get_emoji(emoji.team_emoji_ids.get(team))}\n'
    print(description)
    
def make_plot(data,colors,year,session_type):
    f1plt.setup_mpl()
    fig, ax = plt.subplots(1, figsize=(13,9))
    fig.set_facecolor('black')
    ax.set_facecolor('black')
    fig.suptitle(f'{year} {session_type.name} Head to Head',fontproperties=bold_font,size=20,y=0.95)
    offset = 0
    driver_names = []
    for team in data.keys():
        for pairing in data.get(team).keys():
            drivers = list(data.get(team).get(pairing).keys())
            driver_wins = list(data.get(team).get(pairing).values())
            # print(data.get(team))
            driver_wins[1] = -1 * driver_wins[1]
            # print(drivers)
            # print(driver_wins)
            color = ''
            if not ((colors.get(team).lower() == 'nan') | (colors.get(team).lower() == '')):
                color = f'#{colors.get(team).lower()}'
            ax.barh(pairing, driver_wins, color = color,)# edgecolor = 'black')
            # url = f'https://cdn.discordapp.com/emojis/{emoji.team_emoji_ids.get(team)}.webp?&quality=lossless'
            # print(url)
            # with urllib.request.urlopen(url) as url:
            #     f = io.BytesIO(url.read())
            # image = Image.open(f)
            # image = np.array(image)
            image = mpim.imread(f'lib/cars/logos/{team}.webp')
            zoom = .2
            imagebox = OffsetImage(image, zoom=zoom)
            ab = AnnotationBbox(imagebox, (0, offset), frameon=False)
            ax.add_artist(ab)
            
            for i in range(len(drivers)):
                
                if driver_wins[i] <= 0:
                    driver_name = f'{list(data.get(team).get(pairing).keys())[i]}'
                    driver_names.append(driver_name)
                    wins_string = f'{-1*driver_wins[i]}'
                    ax.text(min(driver_wins[i] - 0.6,-1.2), offset-0.2, wins_string, fontproperties=regular_font, fontsize=20, horizontalalignment='right',path_effects=[pe.withStroke(linewidth=4, foreground="black")])
                else:
                    driver_name = f'{list(data.get(team).get(pairing).keys())[i]}'
                    driver_names.append(driver_name)
                    wins_string = f'{driver_wins[i]}'
                    ax.text(driver_wins[i] + 0.6, offset-0.2, wins_string, fontproperties=regular_font, fontsize=20, horizontalalignment='left',path_effects=[pe.withStroke(linewidth=4, foreground="black")])
                    
            # ax.text(driver_wins, pairing,'hi')
            # for position in enumerate(driver_wins):
            # for i in range(len(drivers)):
            #     x = 0
            #     wins_string = ''
            #     team_data = data.get(team).get(pairing)
            #     # print(drivers[i])
            #     print(team_data)
                
                
            #     if (driver_wins[i] <= 0):
            #         index_of_driver = list(team_data.values()).index(driver_wins[i]*-1)
            #         print(str(int(not(bool(index_of_driver)))))
            #         wins_string = f"{str(-1*driver_wins[i])} {list(team_data.keys())[int(not(bool(index_of_driver)))]}"
            #         print(wins_string)
            #         x = driver_wins[i] -0.4
            #     else:
            #         index_of_driver = list(team_data.values()).index(driver_wins[i])
            #         # print(str(int(not(bool(index_of_driver)))))
            #         wins_string = f"{list(team_data.keys())[index_of_driver]} {str(driver_wins[i])}"
            #         print(wins_string)
            #         x = driver_wins[i] + 0.4
                    
            #     # print(x)
            #     if (x < 0):
            #         ax.text(x, offset-0.2, wins_string, fontproperties=regular_font, fontsize=20, horizontalalignment='right',path_effects=[pe.withStroke(linewidth=4, foreground="black")])
            #     else:
            #         ax.text(x, offset-0.2, wins_string, fontproperties=regular_font, fontsize=20, horizontalalignment='left',path_effects=[pe.withStroke(linewidth=4, foreground="black")])
            offset += 1
    xabs_max = abs(max(ax.get_xlim(), key=abs))+7
    ax.set_xlim(xmin=-xabs_max, xmax=xabs_max)
    offset = 0
    for i in range(len(driver_names)):
        if (i % 2) == 0:
            ax.text(xabs_max, offset-0.2, driver_names[i], fontproperties=bold_font, fontsize=20, horizontalalignment='right',path_effects=[pe.withStroke(linewidth=4, foreground="black")])
        else:
            ax.text(-xabs_max, math.floor(offset)-0.2, driver_names[i], fontproperties=bold_font, fontsize=20, horizontalalignment='left',path_effects=[pe.withStroke(linewidth=4, foreground="black")])
        offset+=0.5
    # yabs_max = abs(max(ax.get_ylim(), key=abs))
    # ax.set_ylim(ymin=-yabs_max, ymax=yabs_max)
    plt.show()
    

def main(year, session_type):
    if (year is None):
        year = now.year
        if cm.currently_offseason()[0]:
            year = year - 1
    
    data,colors = get_data(year, session_type)
    
    # for country in countries.values():
    #     print(f":flag_{coco.convert(names=country,to="ISO2",not_found=None).lower()}:")
    print_data(data)
    # for team in colors.keys():
    #     print(f'{team}: {colors.get(team)}')
    make_plot(data,colors,year,session_type)
    # h2h_embed(data,year,session_type)
    # print(out)
    
sessiontype = session_type('Race','r')
main(2023, sessiontype)
