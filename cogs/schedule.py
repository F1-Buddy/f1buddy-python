import asyncio
import traceback
import discord
import fastf1
import pandas as pd
import country_converter as coco
import requests
import json
import config
from discord import app_commands
from discord.ext import commands
from bs4 import BeautifulSoup
import repeated.embed as em
import repeated.common as cm

fastf1.Cache.enable_cache('cache/')

def countdown(totalseconds):
    out_string = ""
    days = int(totalseconds // 86400)
    totalseconds %= 86400
    hours = int(totalseconds // 3600)
    totalseconds %= 3600
    minutes = int(totalseconds // 60)
    seconds = totalseconds % 60
    seconds = int(seconds // 1)
    out_string += f"{days} days, {hours} hours, {minutes} minutes, and {seconds} seconds until the race!"
    return out_string

def get_weather_data(location):
    weatherURL = "https://weatherapi-com.p.rapidapi.com/forecast.json"
    querystring = {"q":location,"days":"3"}
    headers = {
        "X-RapidAPI-Key": config.weatherapiKEY,
        "X-RapidAPI-Host": 'weatherapi-com.p.rapidapi.com'
    }
    response = requests.request("GET", weatherURL, headers=headers, params=querystring)
    results = json.loads(response.content)
    forecast = results['forecast']['forecastday']
    weather_string = ""
    precip_string = ""
    for i in range(len(forecast)):
        weather_string += ((str)(forecast[i]['day']['avgtemp_c'])+' °C\n')
        precip_string += ((str)(forecast[i]['day']['totalprecip_mm'])+' mm\n')
    return weather_string,precip_string

def get_schedule():
    try:
        now = pd.Timestamp.now().tz_localize('America/New_York')
   
        # for testing
        # now = pd.Timestamp(year=2023, month=5, day=6).tz_localize('America/New_York')
        # now = now + pd.DateOffset(days=-14)

        schedule = fastf1.get_event_schedule(now.year, include_testing=False)
        off_season = any(cm.currently_offseason())
        
        # for testing
        # off_season = False
        
        if off_season:
            dc_embed = em.OffseasonEmbed()
            return dc_embed
        else:
            # get next event
            next_event = cm.latest_completed_index(year=now.year) + 1

            # convert each session to EST  
            if (schedule.loc[next_event, "EventFormat"] == 'conventional'):
                converted_session_times = {
                    f":one: {schedule.loc[next_event, 'Session1']}": schedule.loc[next_event, "Session1DateUtc"],
                    f":two: {schedule.loc[next_event, 'Session2']}": schedule.loc[next_event, "Session2DateUtc"],
                    f":three: {schedule.loc[next_event, 'Session3']}": schedule.loc[next_event, "Session3DateUtc"],
                    f":stopwatch: {schedule.loc[next_event, 'Session4']}": schedule.loc[next_event, "Session4DateUtc"],
                    f":checkered_flag: {schedule.loc[next_event, 'Session5']}": schedule.loc[next_event, "Session5DateUtc"]
                }
            else:
                converted_session_times = {
                    f":one: {schedule.loc[next_event, 'Session1']}": schedule.loc[next_event, "Session1DateUtc"],
                    f":stopwatch: {schedule.loc[next_event, 'Session2']}": schedule.loc[next_event, "Session2DateUtc"],
                    f":stopwatch: {schedule.loc[next_event, 'Session3']}": schedule.loc[next_event, "Session3DateUtc"],
                    f":race_car: {schedule.loc[next_event, 'Session4']}": schedule.loc[next_event, "Session4DateUtc"],
                    f":checkered_flag: {schedule.loc[next_event, 'Session5']}": schedule.loc[next_event, "Session5DateUtc"]
                }
            for key in converted_session_times.keys():
                date_object = converted_session_times.get(key).tz_localize("UTC").tz_convert('America/New_York')
                converted_session_times.update({key: date_object})
            
            # strings to be added to embed fields
            sessions_string = ''
            times_string = ''
            for key in converted_session_times.keys():
                curr_time = converted_session_times.get(key)
                tdelta = int((curr_time - pd.Timestamp("1970-01-01").tz_localize('UTC')) / pd.Timedelta('1s'))
                times_string += f'<t:{tdelta}:f>\n'
                # times_string += '`'+(converted_session_times.get(key)).strftime('%I:%M%p on %Y/%m/%d') + "`\n"
                sessions_string += key + '\n'
            
            # more strings for embed
            race_name = schedule.loc[next_event, 'EventName'][:-11] + " GP"
            emoji = ":flag_" + (coco.convert(names=schedule.loc[next_event, "Country"], to='ISO2')).lower()+":"
            time_until = schedule.loc[next_event, "Session5DateUtc"].tz_localize("UTC").tz_convert('America/New_York') - now
            description_string = countdown(time_until.total_seconds())
            title_string = "Race Schedule for "+emoji+"**" + race_name + "**" + emoji
            
            # get track image
            url = f"https://www.formula1.com/en/racing/{now.year}/{schedule.loc[next_event,'EventName'][:-11]}/Circuit.html"
            response = requests.get(url)
            soup = BeautifulSoup(response.content, 'html.parser')
            image = soup.find_all('img')
            for i in image:
                if 'circuit' in str(i.get('alt')).lower():
                    track_url = (i.get('data-src'))
            
            # add final fields to embed
            dc_embed = em.Embed(title=title_string, description=description_string, image_url=track_url)
            dc_embed.embed.add_field(name="Session", value=sessions_string,inline=True)
            dc_embed.embed.add_field(name="Time", value=times_string,inline=True)
            
            # get weather data if race is within 3 days
            time_to_race = converted_session_times.get(":checkered_flag: Race")-now
            race_within_3days = time_to_race.total_seconds() < 259200
            if (race_within_3days):
                weather_string, precip_string = get_weather_data(schedule.loc[next_event, "Location"])
                days = "Friday\nSaturday\nSunday"
                dc_embed.embed.add_field(name="Weather Forecast:", value="",inline=False)
                dc_embed.embed.add_field(name="Day", value=days,inline=True)
                dc_embed.embed.add_field(name="Temperature", value=weather_string,inline=True)
                dc_embed.embed.add_field(name="Precipitation", value=precip_string,inline=True)
            else:
                dc_embed.embed.set_footer(text="Weather forecast available within 72 hours of race*") 
            return dc_embed
    except Exception as e:
        traceback.print_exc()
        return em.ErrorEmbed(error_message=e)
   
class Schedulenew(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        print('Schedule cog loaded')

    @app_commands.command(name='schedule', description='get F1 race schedule')
    async def schedule(self, interaction: discord.Interaction):
        await interaction.response.defer()
        # defer response
        try:
            loop = asyncio.get_running_loop()   
            dc_embed = await loop.run_in_executor(None, get_schedule)
            await interaction.followup.send(embed=dc_embed.embed)
        except Exception as e:
            print(e)
            # print(traceback.print_stack())
        
        
async def setup(bot):
    await bot.add_cog(Schedulenew(bot))