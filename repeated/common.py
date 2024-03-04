# common functions
import fastf1
import pandas as pd

fastf1.Cache.enable_cache('cache/')

class YearNotValidException(Exception):
    pass
class RoundNotValidException(Exception):
    pass

def currently_offseason():
    now = pd.Timestamp.now().tz_localize('America/New_York')
    schedule = fastf1.get_event_schedule(now.year, include_testing=False)
    first_event_index = schedule.index[0]
    first_event_date = schedule.loc[first_event_index,'Session5DateUtc'].tz_localize("UTC")
    # say its off season if more than 2 weeks away from first race
    first_event_date = first_event_date + pd.DateOffset(days=-14)
    last_event_index = schedule.index[len(schedule.index)-1]
    last_event_date = schedule.loc[last_event_index,'Session5DateUtc'].tz_localize("UTC")
    season_complete = (last_event_date < now)
    season_not_started = (now < first_event_date)
    return [season_not_started,season_complete]

def latest_completed_index(year):
    now = pd.Timestamp.now().tz_localize('America/New_York')
    # now = pd.Timestamp(2024,5,2).tz_localize('America/New_York') #miami may 05
    # now = pd.Timestamp(2024,10,17).tz_localize('America/New_York') #cota oct 20
    # now = pd.Timestamp(2024,11,19).tz_localize('America/New_York') #las vegas nov 23
    # for testing
    # now = pd.Timestamp(year=2023, month=5, day=6).tz_localize('America/New_York')
    schedule = fastf1.get_event_schedule(year, include_testing=False)
    first_index = schedule.index[0]
    next_event = first_index
    curr_event_date = schedule.loc[next_event,'Session5DateUtc'].tz_localize("UTC")
    # print(f'curr_event_date > now?: {curr_event_date > now}')
    if (curr_event_date > now):
        return 0
    while ((curr_event_date < now) & (next_event < schedule.index[len(schedule.index)-1]) ):
        # print(schedule.loc[next_event,'EventName'])
        next_event += 1
        curr_event_date = schedule.loc[next_event,'Session5DateUtc'].tz_localize("UTC")
    # print(schedule.loc[next_event,'EventName'])
    return next_event

def latest_quali_completed_index(year):
    now = pd.Timestamp.now().tz_localize('America/New_York')
    # now = pd.Timestamp(2024,5,2).tz_localize('America/New_York') #miami may 05
    # now = pd.Timestamp(2024,10,17).tz_localize('America/New_York') #cota oct 20
    # now = pd.Timestamp(2024,11,19).tz_localize('America/New_York') #las vegas nov 23
    # for testing
    # now = pd.Timestamp(year=2023, month=5, day=6).tz_localize('America/New_York')
    schedule = fastf1.get_event_schedule(year, include_testing=False)
    first_index = schedule.index[0]
    next_event = first_index
    curr_event_date = schedule.loc[next_event,'Session4DateUtc'].tz_localize("UTC")
    # print(f'curr_event_date > now?: {curr_event_date > now}')
    if (curr_event_date > now):
        return 0
    while ((curr_event_date < now) & (next_event < schedule.index[len(schedule.index)-1]) ):
        # print(schedule.loc[next_event,'EventName'])
        next_event += 1
        curr_event_date = schedule.loc[next_event,'Session4DateUtc'].tz_localize("UTC")
    # print(schedule.loc[next_event,'EventName'])
    return next_event

# create function for input checking (year/round)
def check_year(year,data=None,quali=False):
    now = pd.Timestamp.now().tz_localize('America/New_York')
    upper_lim = now.year
    if not quali:
        if (latest_completed_index(upper_lim) == 0): 
            upper_lim -= 1
    else:
        if (latest_quali_completed_index(upper_lim) == 0): 
            upper_lim -= 1
    if year is None:
        return upper_lim
    if (data):
        if (year < 2018) or (year > upper_lim):
            raise YearNotValidException(f"Year is invalid. Valid range for this data is 2018-{upper_lim}")
        else:
            return year
    else:
        if (year < 1958) or (year > upper_lim):
            raise YearNotValidException(f"Year is invalid. Valid range for this data is 1958-{upper_lim}")
        else:
            return year
        