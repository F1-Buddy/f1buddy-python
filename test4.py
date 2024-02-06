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
        
    schedule = fastf1.get_event_schedule(year=year,include_testing=False)
    for c in range(min(schedule.index), max(schedule.index)+1):
    # for c in range(min(schedule.index),min(schedule.index)+1):
        session = fastf1.get_session(year, schedule.loc[c,'RoundNumber'], session_type.value)
        session.load(laps=False, telemetry=False, weather=False, messages=False)
        results = session.results
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
            # if (i == "Red Bull Racing"):
            #     print(team_results)
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
                if ((team_results.loc[driver,'ClassifiedPosition']) in dnf):
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
            
            
    return team_list
        
        
    # print(schedule)
    
def main(year, session_type):
    if (year is None):
        year = now.year
        if cm.currently_offseason()[0]:
            year = year - 1
    # clean year
    data = get_data(year, session_type)
    for team in data.keys():
        print(team)
        for pairing in data.get(team).keys():
            print(f'    {pairing}:')
            for driver in data.get(team).get(pairing):
                if not (driver == 'round_updated'):
                    print(f'        {driver}: {data.get(team).get(pairing).get(driver)}')
    
sessiontype = session_type('Race','r')
main(2023, sessiontype)