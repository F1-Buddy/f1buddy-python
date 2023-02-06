# https://github.com/theOehrly/Fast-F1/issues/253
# fast-f1 lacks standardized time zones for events, all events are listed in local track time

import discord
import fastf1
import pandas as pd
from discord import app_commands
from discord.ext import commands
from geopy.geocoders import Nominatim
from timezonefinder import TimezoneFinder

class Schedule(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # print('hi')
    @commands.Cog.listener()
    async def on_ready(self):
        print('schedule cog loaded')

    # @commands.command()
    # async def sync(self, ctx) -> None:
    #     fmt = await ctx.bot.tree.sync(guild=ctx.guild)
    #     await ctx.send(f'Synced {len(fmt)}')

    @app_commands.command(name='schedule', description='get race schedule')
    async def schedule(self, interaction: discord.Interaction):
        await interaction.response.defer()
        now = pd.Timestamp.now()
        message_embed = discord.Embed(title="Race Schedule", description="")
        message_embed.set_thumbnail(url='https://cdn.discordapp.com/attachments/884602392249770087/1059464532239581204/f1python128.png')

        # schedule object
        schedule = fastf1.get_event_schedule(2022, include_testing=False)

        next_event = 0
        test_time = pd.Timestamp(year=2022, month=9, day=3)
        out_string = ""

        
        # for i in range(len(schedule)):
        #     if schedule.iloc[i].values[4] < now:
        #         next_event = i+1

        # range starts at 2 because I skip 0 and 1 since I ignore preseason testing sessions
        # find round number of next event
        for i in range(2,len(schedule)):
            if schedule.loc[i,"Session1Date"] < test_time:
                next_event = i+1
        
        # get nearest FP1 session including past
        # check if race event has passed, if not then set index back by 1
        if ((schedule.loc[next_event,"Session5Date"]-test_time).total_seconds()>0):
            next_event -= 1

        # gets session times for weekend
        session_times = {
            "fp1_time": schedule.iloc[next_event].values[8],
            "fp2_time": schedule.iloc[next_event].values[10],
            "fp3_time": schedule.iloc[next_event].values[12],
            "quali_time": schedule.iloc[next_event].values[14],
            "race_time": schedule.iloc[next_event].values[16]
        }
        print(session_times)
        
        try:        
            converted_session_times = {
                "fp1_time": schedule.iloc[next_event].values[8],
                "fp2_time": schedule.iloc[next_event].values[10],
                "fp3_time": schedule.iloc[next_event].values[12],
                "quali_time": schedule.iloc[next_event].values[14],
                "race_time": schedule.iloc[next_event].values[16]
            }

            for value in converted_session_times.values():
                date_object = value
                g = Nominatim(user_agent='f1pythonbottesting')
                location = schedule.iloc[next_event].values[2]
                coords = g.geocode(location)
                # print(coords)
                tf = TimezoneFinder()
                tz = tf.timezone_at(lng=coords.longitude, lat=coords.latitude)
                date_object = date_object.tz_localize(tz).tz_convert('America/New_York')
                value = date_object

            print(converted_session_times)
            date = str(schedule.iloc[next_event].values[4].month) + "/"+ str(schedule.iloc[next_event].values[4].day)+"/"+ str(schedule.iloc[next_event].values[4].year)
            time = str(date_object)[str(date_object).index(":")-2:]
            time = time[:time.index("-")]

            out_string = ''.join([
                'Next event is the \n',
                str(schedule.iloc[next_event].values[3]),
                '\non **',
                date,
                '**\nat **',
                time,
                " EST** "
            ])

            # # TIME IS IN LOCAL NOT UTC
            # date_object = schedule.iloc[next_event].values[16]
            # g = Nominatim(user_agent='f1pythonbottesting')
            # location = schedule.iloc[next_event].values[2]
            # coords = g.geocode(location)
            # # print(coords)
            # tf = TimezoneFinder()
            # tz = tf.timezone_at(lng=coords.longitude, lat=coords.latitude)
            # date_object = date_object.tz_localize(tz).tz_convert('America/New_York')

            # date = str(schedule.iloc[next_event].values[4].month) + "/"+ str(schedule.iloc[next_event].values[4].day)+"/"+ str(schedule.iloc[next_event].values[4].year)
            # time = str(date_object)[str(date_object).index(":")-2:]
            # time = time[:time.index("-")]

            # out_string = ''.join([
            #     'Next event is the \n',
            #     str(schedule.iloc[next_event].values[3]),
            #     '\non **',
            #     date,
            #     '**\nat **',
            #     time,
            #     " EST** "
            # ])
        except IndexError:
            out_string = ('It is currently off season! :crying_cat_face:')
        # print(out_string)
        # Remove question field
        #######################################################################
        # outstring = 'message received = ' + question
        # print(outstring)
        await interaction.followup.send(content=out_string)


async def setup(bot):
    await bot.add_cog(Schedule(bot), guilds=[discord.Object(id=884602392249770084)])