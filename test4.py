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
    team_fullName = {}
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
            print(team_results)
            # print(team_results[['Abbreviation','ClassifiedPosition','Status','TeamColor','TeamId']])
                
            # dictionary format:
            # teamName:
            #   driverPairing:
            #       driver: #ofRacesFinishedAheadofTeammate
            #       otherDriver: #ofRacesFinishedAheadofTeammate
            if (team_list.get(i) is None):
                team_fullName.update({i:team_results.loc[min(team_results.index),'TeamName']})
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
            if (sessiontype.value == 'r'):
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
    return team_list,color_list, team_fullName #, outstring

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
    
def make_plot(data,colors,year,session_type, team_names, file_path):
    try:
        plt.clf()
        f1plt.setup_mpl()
        fig, ax = plt.subplots(1, figsize=(13,9))
        fig.set_facecolor('black')
        ax.set_facecolor('black')
        fig.suptitle(f'{year} {session_type.name} Head to Head',fontproperties=bold_font,size=20,y=0.95)
        offset = 0
        driver_names = []
        y_ticks = []
        for team in data.keys():
            for pairing in data.get(team).keys():
                y_ticks.append(team_names.get(team))
                drivers = list(data.get(team).get(pairing).keys())
                driver_wins = list(data.get(team).get(pairing).values())
                # flip second driver to draw back to back
                driver_wins[1] = -1 * driver_wins[1]
                # team color
                color = ''
                if not ((colors.get(team).lower() == 'nan') | (colors.get(team).lower() == '')):
                    color = f'#{colors.get(team).lower()}'
                ax.barh(pairing, driver_wins, color = color,)# edgecolor = 'black')
                # team logo
                img = mpim.imread(f'lib/cars/logos/{team}.webp')
                zoom = .2
                imagebox = OffsetImage(img, zoom=zoom)
                ab = AnnotationBbox(imagebox, (0, offset), frameon=False)
                ax.add_artist(ab)
                
                # label the bars
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
                offset += 1
        # plot formatting
        left = min(fig.subplotpars.left, 1 - fig.subplotpars.right)
        bottom = min(fig.subplotpars.bottom, 1 - fig.subplotpars.top)
        fig.subplots_adjust(left=left, right=1 - left, bottom=bottom, top=1 - bottom)
        ax.get_xaxis().set_visible(False)
        ax.get_yaxis().set_visible(False)
        ax.set_yticklabels(y_ticks, fontproperties=regular_font, fontsize=10)
        ax.spines['top'].set_visible(False)
        ax.spines['bottom'].set_visible(False)
        ax.spines['left'].set_visible(False)
        ax.spines['right'].set_visible(False)
        xabs_max = abs(max(ax.get_xlim(), key=abs))+7
        
        # watermark
        watermark_img = plt.imread('botPics/f1pythoncircular.png')
        watermark_box = OffsetImage(watermark_img, zoom=0.22) 
        ab = AnnotationBbox(watermark_box, (-0.06,1.05), xycoords='axes fraction', frameon=False)
        ax.add_artist(ab)
        ax.text(0.1,1.03, 'Made by\nF1Buddy Discord Bot', transform=ax.transAxes,
                fontsize=13,fontproperties=bold_font, ha='center')
        
        ax.yaxis.grid(False)
        ax.set_xlim(xmin=-xabs_max, xmax=xabs_max)
        offset = 0
        # label drivers
        for i in range(len(driver_names)):
            if (i % 2) == 0:
                ax.text(xabs_max, offset-0.2, driver_names[i], fontproperties=bold_font, fontsize=20, horizontalalignment='right',path_effects=[pe.withStroke(linewidth=4, foreground="black")])
            else:
                ax.text(-xabs_max, math.floor(offset)-0.2, driver_names[i], fontproperties=bold_font, fontsize=20, horizontalalignment='left',path_effects=[pe.withStroke(linewidth=4, foreground="black")])
            offset+=0.5
        
        plt.show()
    except:
        traceback.print_exc()
    # plt.rcParams['savefig.dpi'] = 300
    # plt.savefig(file_path)
    
    

def main(year, session_type):
    if (year is None):
        year = now.year
        if cm.currently_offseason()[0]:
            year = year - 1
    
    folder_path = f'./cogs/plots/h2h/{year}/{session_type.name}'
    file_path = f'./cogs/plots/h2h/{year}/{session_type.name}/{cm.latest_completed_index(year)}.png'
    data,colors,names = get_data(year, session_type)
    if not (os.path.exists(file_path)):
        if not os.path.exists(folder_path):
            os.makedirs(folder_path)
        try:
            make_plot(data,colors,year,session_type,names,file_path)    
        except:
            return em.ErrorEmbed('Error while drawing', error_message=traceback.format_exc()), None
    # file = discord.File(file_path,filename="image.png")
    # return em.Embed(title=title,image_url='attachment://image.png'), file
        

    
sessiontype = session_type('Qualifying','q')
main(2023, sessiontype)
