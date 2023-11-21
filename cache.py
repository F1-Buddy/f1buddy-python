# caching script
# run with or without cli args

# ex:
# load light quali + race data for current season (excludes laps, telem, weather, and messages data)
# python cache.py 

# load all quali + race data for given season
# python cache.py 2020 True

import fastf1
import sys
import pandas as pd

fastf1.Cache.enable_cache('cache/')
now = pd.Timestamp.now()

n = len(sys.argv) - 1
allData = False
numRaces = 0
schedule = None
errorString = ''

if (n == 0):
    schedule = fastf1.get_event_schedule(now.year, include_testing=False)
    year = now.year

if n == 2:
    year = int(sys.argv[1])
    schedule = fastf1.get_event_schedule(year, include_testing=False)
    if sys.argv[2].lower() == 'true':
        allData = True
    
    
numRaces = len(schedule)+1

for i in range(1,numRaces):
    try:
        try:
            race = fastf1.get_session(year, i, 'Q')
            race.load(laps=allData,telemetry=allData,weather=allData,messages=allData)
        except fastf1.core.DataNotLoadedError:
            racename = schedule.loc[i,'EventName']
            errorString +=(f"quali data not loaded for {racename}(session probably hasn't happened yet)\n")
        try:            
            race = fastf1.get_session(year, i, 'R')
            race.load(laps=allData,telemetry=allData,weather=allData,messages=allData)
        except fastf1.core.DataNotLoadedError:
            racename = schedule.loc[i,'EventName']
            errorString +=(f"race data not loaded for {racename}(session probably hasn't happened yet)\n")
    except Exception as e:
        errorString += e+"\n"

print(errorString)
    