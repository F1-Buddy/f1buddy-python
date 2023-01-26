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
        # test_time = pd.Timestamp(year=2022, month=9, day=3)
        out_string = ""

        
        for i in range(len(schedule)):
            if schedule.iloc[i].values[4] < now:
                next_event = i+1
        try:        
            # TIME IS IN LOCAL NOT UTC
            date_object = schedule.iloc[next_event].values[16]
            # print('race start = ',date_object, ' local time')
            # session = fastf1.get_session(date_object.year,schedule.iloc[next_event].values[0],'R')
            g = Nominatim(user_agent='f1pythonbottesting')
            location = schedule.iloc[next_event].values[2]
            coords = g.geocode(location)
            # print(coords)
            tf = TimezoneFinder()
            tz = tf.timezone_at(lng=coords.longitude, lat=coords.latitude)
            date_object = date_object.tz_localize(tz).tz_convert('America/New_York')

            date = str(schedule.iloc[next_event].values[4].month) + "/"+ str(schedule.iloc[next_event].values[4].day)+"/"+ str(schedule.iloc[next_event].values[4].year)
            time = str(date_object)[str(date_object).index(":")-2:]
            time = time[:time.index("-")]
            # print(date_object)
            # print(date_object.tz_convert('America/New_York'))
            # print(tz)
            # session.load()
            # print(session.date)
            # print(date_object)
            # print('country = ',schedule.iloc[next_event].values[1])
            # print('location = ',schedule.iloc[next_event].values[2])

            out_string = ''.join([
                'Next event is the \n',
                str(schedule.iloc[next_event].values[3]),
                '\non **',
                date,
                '**\nat **',
                time,
                " EST** "
            ])
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