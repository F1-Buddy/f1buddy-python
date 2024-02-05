# common functions
import fastf1
import pandas as pd

fastf1.Cache.enable_cache('cache/')

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
    # for testing
    # now = pd.Timestamp(year=2023, month=5, day=6).tz_localize('America/New_York')
    schedule = fastf1.get_event_schedule(year, include_testing=False)
    first_index = schedule.index[0]
    next_event = first_index
    curr_event_date = schedule.loc[next_event,'Session5DateUtc'].tz_localize("UTC")
    while ((curr_event_date < now) & (next_event < schedule.index[len(schedule.index)-1]) ):
        # print(schedule.loc[next_event,'EventName'])
        next_event += 1
        curr_event_date = schedule.loc[next_event,'Session5DateUtc'].tz_localize("UTC")
    # print(schedule.loc[next_event,'EventName'])
    return next_event
