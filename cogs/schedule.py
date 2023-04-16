# https://github.com/theOehrly/Fast-F1/issues/253
# fast-f1 lacks standardized time zones for events, all events are listed in local track time

import discord
import fastf1
import lib.timezones as timezones
import pandas as pd
import datetime
import country_converter as coco
import requests
import json
import config
from discord import app_commands
from discord.ext import commands
from geopy.geocoders import Nominatim
from timezonefinder import TimezoneFinder
from bs4 import BeautifulSoup
from lib.station_codes import stations

fastf1.Cache.enable_cache('cache/')

# fallback function to calculate timezone using lat/long if 
# a suitable timezone is not found in timezones.py
def convert_timezone_fallback(location, converted_session_times):
    # create coordinate finder object
    g = Nominatim(user_agent='f1pythonbottesting')
    # get coordinates of track
    coords = g.geocode(location)
    print(location + ": " + (str)(coords.latitude) + " , " + (str)(coords.longitude))

    # create timezone finder object
    tf = TimezoneFinder()

    # find track timezone using its coordinates
    tz = tf.timezone_at(lng=coords.longitude, lat=coords.latitude)
    # update dictionary with converted times
    for key in converted_session_times.keys():
        date_object = converted_session_times.get(key).tz_localize(
            tz).tz_convert('America/New_York')
        converted_session_times.update({key: date_object})
        # print(date_object)


class Schedule(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        print('Schedule cog loaded')

    @app_commands.command(name='schedule', description='get race schedule')
    async def schedule(self, interaction: discord.Interaction):
        # defer response
        await interaction.response.defer()
        # timestamp for now to find next event
        now = pd.Timestamp.now()

        # setup embed
        message_embed = discord.Embed(title="Schedule", description="")
        message_embed.colour = discord.Colour.dark_red()
        message_embed.set_thumbnail(
            url='https://cdn.discordapp.com/attachments/884602392249770087/1059464532239581204/f1python128.png')

        # schedule object
        schedule = fastf1.get_event_schedule(2023, include_testing=True)

        # index of next event (round number)
        next_event = 0
        ################################################################
        # TESTING TIMESTAMP
        # change date to test schedule command on that date
        # now = pd.Timestamp(year=2023, month=4, day=29)
        ################################################################

        # string to hold final message
        out_string = "It is currently `" + now.strftime('%I:%M%p on %Y/%m/%d') + "`\n\n"

        # range starts at 2 because I skip 0 and 1 since I ignore preseason testing sessions
        # find round number of next event
        for i in range(0, len(schedule)):
            next_event = i+1
            # if (fp1 < now < race) --> scenario where today is before the next race but after this weekend's fp1
            # or
            # if (fp1 > now > last race) --> scenario where today is after the last race but before upcoming race weekend's fp1
            location_1 = schedule.loc[i, "Location"]
            local_tz_1 =  timezones.timezones_list[location_1]
            fp1_session = schedule.loc[i, "Session1Date"].tz_localize(local_tz_1).tz_convert('America/New_York')
            race_session = schedule.loc[i, "Session5Date"].tz_localize(local_tz_1).tz_convert('America/New_York')
            try:
                location_2 = schedule.loc[i-1, "Location"]
                local_tz_2 =  timezones.timezones_list[location_2]
                last_race_session = schedule.loc[i-1, "Session5Date"].tz_localize(local_tz_2).tz_convert('America/New_York')
            except:
                continue
            if ((fp1_session < now.tz_localize('America/New_York')) and (race_session > now.tz_localize('America/New_York'))) or ((fp1_session > now.tz_localize('America/New_York'))) or ((fp1_session > now.tz_localize('America/New_York')) and (last_race_session < now.tz_localize('America/New_York'))):
                next_event -= 1
                # print statements for testing
                # temp_race_name = schedule.loc[i,"EventName"]
                # print("\n"+temp_race_name + " FP1 < now < "+temp_race_name+"?")
                # print(((schedule.loc[i,"Session1Date"] < now) and (schedule.loc[i,"Session5Date"] > now)))
                # print(temp_race_name + " FP1 > now > "+schedule.loc[i-1,"EventName"]+"?")
                # print(((schedule.loc[i,"Session1Date"] > now) and (schedule.loc[i-1,"Session5Date"] < now)))
                break

        try:
            # check if it is off season
            if (len(schedule) <= next_event):
                raise IndexError

            # else
            # get name of event
            race_name = schedule.loc[next_event, "EventName"]


            # get emoji for country
            emoji = ":flag_" + \
                (coco.convert(
                    names=schedule.loc[next_event, "Country"], to='ISO2')).lower()+":"

            # Rename embed title
            message_embed.title = "Race Schedule for "+emoji+"**" + race_name + "**" + emoji

            # create a dictionary to store converted times
            # adjust emojis/session name according to weekend format
            if (schedule.loc[next_event, "EventFormat"] == 'conventional'):
                converted_session_times = {
                    ":one: FP1": schedule.loc[next_event, "Session1Date"],
                    ":two: FP2": schedule.loc[next_event, "Session2Date"],
                    ":three: FP3": schedule.loc[next_event, "Session3Date"],
                    ":stopwatch: Qualifying": schedule.loc[next_event, "Session4Date"],
                    ":checkered_flag: Race": schedule.loc[next_event, "Session5Date"]
                }
                fp1_date = pd.Timestamp(converted_session_times[":one: FP1"]).strftime('%Y-%m-%d')
                fp2_date = pd.Timestamp(converted_session_times[":two: FP2"]).strftime('%Y-%m-%d')
                fp3_date = pd.Timestamp(converted_session_times[":three: FP3"]).strftime('%Y-%m-%d')
                quali_date = pd.Timestamp(converted_session_times[":stopwatch: Qualifying"]).strftime('%Y-%m-%d')
                race_date = pd.Timestamp(converted_session_times[":checkered_flag: Race"]).strftime('%Y-%m-%d')
            else:
                converted_session_times = {
                    ":one: FP1": schedule.loc[next_event, "Session1Date"],
                    ":two: FP2": schedule.loc[next_event, "Session2Date"],
                    ":stopwatch: Qualifying": schedule.loc[next_event, "Session3Date"],
                    ":race_car: Sprint": schedule.loc[next_event, "Session4Date"],
                    ":checkered_flag: Race": schedule.loc[next_event, "Session5Date"]
                }
                fp1_date = pd.Timestamp(converted_session_times[":one: FP1"]).strftime('%Y-%m-%d')
                fp2_date = pd.Timestamp(converted_session_times[":two: FP2"]).strftime('%Y-%m-%d')
                quali_date = pd.Timestamp(converted_session_times[":stopwatch: Qualifying"]).strftime('%Y-%m-%d')
                sprint_date = pd.Timestamp(converted_session_times[":race_car: Sprint"]).strftime('%Y-%m-%d')
                race_date = pd.Timestamp(converted_session_times[":checkered_flag: Race"]).strftime('%Y-%m-%d')
            
            try:
                # get location of race
                location = schedule.loc[next_event, "Location"]
                # try to get timezone from list
                local_tz = timezones.timezones_list[location]
                # print("Getting timezone from timezones.py")
                # convert times to EST
                for key in converted_session_times.keys():
                    date_object = converted_session_times.get(key).tz_localize(
                        local_tz).tz_convert('America/New_York')
                    converted_session_times.update({key: date_object})
            # timezone not found in timezones.py
            except Exception as e:
                print("Using fallback timezone calculation")
                print(e)
                # calculate timezone using latitude/longitude
                convert_timezone_fallback(location,converted_session_times)

            message_embed.set_footer(text="Times are displayed in EST") 
            # strings to store session names and times
            sessions_string = ''
            times_string = ''

            # setup strings to be added to fields
            for key in converted_session_times.keys():
                times_string += '`'+(converted_session_times.get(key)).strftime('%I:%M%p on %Y/%m/%d') + "`\n"
                sessions_string += key + '\n'
                
            # get circuit png url from f1 site, using bs4 to parse through HTML
            current_year = datetime.datetime.now().year
            url = f"https://www.formula1.com/en/racing/{current_year}.html"
            response = requests.get(url)
            soup = BeautifulSoup(response.content, 'html.parser')
            image = soup.find_all('picture', {'class': 'track'})
            image_url = image[next_event-1].find('img')['data-src']

            weatherURL = "https://meteostat.p.rapidapi.com/stations/hourly"
            station_code = stations[race_name]
            
            
            fp1_date = "2023-04-15"
            race_date = "2023-04-22"
            querystring = {"station":station_code,"start":fp1_date,"end":race_date,"tz":"America/New_York"}
            headers = {
                "X-RapidAPI-Key": config.KEY,
                "X-RapidAPI-Host": "meteostat.p.rapidapi.com"
            }
            response = requests.request("GET", weatherURL, headers=headers, params=querystring)
            results = json.loads(response.content)
            for datapoint in results['data']:
                print(f"Time: {datapoint['time']}\tTemperature: {datapoint['temp']} C\tPrecipitation: {datapoint['prcp']}")
            # print(f"{fp1_date}\n{fp2_date}\n{quali_date}\n{sprint_date}\n{race_date}")

            # add fields to embed
            message_embed.add_field(name="Session", value=sessions_string,inline=True)
            message_embed.add_field(name="Time", value=times_string,inline=True)
            message_embed.set_image(url=image_url)
            
        # probably off season / unsure
        except IndexError:
            out_string = ('It is currently off season! :crying_cat_face:')
            message_embed.set_image(
                url='https://media.tenor.com/kdIoxRG4W4QAAAAC/crying-crying-kid.gif')
            message_embed.set_footer(text="*probably*")
        # all other errors
        except Exception as e:
            print(e)
            out_string = "Unknown error occured! Uh-Oh! Bad! :thermometer_face:"

        #######################################################################
        # add final string to embed and send it
        #  ***3/1/2023 ^^ no longer needed since out_string doesnt contain info other than the current time
        message_embed.description = out_string
        await interaction.followup.send(embed=message_embed)


async def setup(bot):
    await bot.add_cog(Schedule(bot))
