# https://github.com/theOehrly/Fast-F1/issues/253
# fast-f1 lacks standardized time zones for events, all events are listed in local track time

import discord
import fastf1
import pandas as pd
from discord import app_commands
from discord.ext import commands
from geopy.geocoders import Nominatim
from timezonefinder import TimezoneFinder
import country_converter as coco

fastf1.Cache.enable_cache('cache/')


class Schedule(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # print('hi')
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
        message_embed = discord.Embed(title="Race Schedule", description="")
        message_embed.set_thumbnail(url='https://cdn.discordapp.com/attachments/884602392249770087/1059464532239581204/f1python128.png')

        # schedule object
        schedule = fastf1.get_event_schedule(2022, include_testing=False)

        # index of next event (round number)
        next_event = 2
        ################################################################
        # timestamp to test function
        # now = pd.Timestamp(year=2022, month=10, day=31)
        ################################################################
        
        
        # string to hold final message
        out_string = "It is currently " + now.strftime('%Y-%m-%d %X') + "\n\n"

        # range starts at 2 because I skip 0 and 1 since I ignore preseason testing sessions
        # find round number of next event
        for i in range(2,len(schedule)):
            next_event = i+1
            # if (fp1 < now < race) --> scenario where today is before the next race but after this weekend's fp1
            # or
            # if (fp1 > now > last race) --> scenario where today is after the last race but before upcoming race weekend's fp1
            if ((schedule.loc[i,"Session1Date"] < now) and (schedule.loc[i,"Session5Date"] > now)) or ((schedule.loc[i,"Session1Date"] > now) and (schedule.loc[i-1,"Session5Date"] < now)):
                next_event -= 1
                # testing
                temp_race_name = schedule.loc[i,"EventName"]
                print("\n"+temp_race_name + " FP1 < now < "+temp_race_name+"?")
                print(((schedule.loc[i,"Session1Date"] < now) and (schedule.loc[i,"Session5Date"] > now)))
                print(temp_race_name + " FP1 > now > "+schedule.loc[i-1,"EventName"]+"?")
                print(((schedule.loc[i,"Session1Date"] > now) and (schedule.loc[i-1,"Session5Date"] < now)))
                break
        
        
        
        try:      
            # check if it is off season
            if (len(schedule) <= next_event):
                raise IndexError
            
            # else
            # get name of event
            race_name = schedule.loc[next_event,"EventName"]
            
            # get emoji for country
            emoji = ":flag_"+(coco.convert(names=schedule.loc[next_event,"Country"],to='ISO2')).lower()+":"
            
            # Rename embed title
            message_embed.title = "Race Schedule for "+emoji+"**" + race_name + "**" + emoji  
            
            # create a dictionary to store converted times
            # adjust emojis/message according to weekend format
            if (schedule.loc[next_event,"EventFormat"] == 'conventional'):
                converted_session_times = {
                    ":one: FP1": schedule.loc[next_event, "Session1Date"],
                    ":two: FP2": schedule.loc[next_event, "Session2Date"],
                    ":three: FP3": schedule.loc[next_event, "Session3Date"],
                    ":stopwatch: Qualifying": schedule.loc[next_event, "Session4Date"],
                    ":checkered_flag: Race": schedule.loc[next_event, "Session5Date"]
                }
            else:
                converted_session_times = {
                    ":one: FP1": schedule.loc[next_event, "Session1Date"],
                    ":two: FP2": schedule.loc[next_event, "Session2Date"],
                    ":stopwatch: Qualifying": schedule.loc[next_event, "Session3Date"],
                    ":race_car: Sprint": schedule.loc[next_event, "Session4Date"],
                    ":checkered_flag: Race": schedule.loc[next_event, "Session5Date"]
                }
            

            # TIME IS IN LOCAL NOT UTC
            # create coordinate finder object
            g = Nominatim(user_agent='f1pythonbottesting')
            # get location of track
            location = schedule.loc[next_event,"Location"]
            # get coordinates of track
            coords = g.geocode(location)

            # create timezone finder object
            tf = TimezoneFinder()
            # find track timezone using its coordinates
            tz = tf.timezone_at(lng=coords.longitude, lat=coords.latitude)

            # update dictionary with converted times
            for key in converted_session_times.keys():
                date_object = converted_session_times.get(key).tz_localize(
                    tz).tz_convert('America/New_York')
                converted_session_times.update({key:date_object})

            # print(converted_session_times)

            out_string += "**Times are displayed in EST**\n\n"

            # add times to string
            for key in converted_session_times.keys():
                out_string += key + ": \t`" + (converted_session_times.get(key)).strftime('%Y/%m/%d %X') + "`\n"

        except IndexError:
            out_string = ('It is currently off season! :crying_cat_face:')
            message_embed.set_image(url='https://media.tenor.com/kdIoxRG4W4QAAAAC/crying-crying-kid.gif')
            message_embed.set_footer(text = "*probably*")
        except:
            out_string = "Unknown error occured! Uh-Oh! Bad! :thermometer_face:"

        #######################################################################
        # add final string to embed and send it
        message_embed.description = out_string
        await interaction.followup.send(embed=message_embed)


async def setup(bot):
    await bot.add_cog(Schedule(bot))