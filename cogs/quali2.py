import discord
import asyncio
import fastf1
import typing
import pandas as pd
from discord import app_commands
from discord.ext import commands
from lib.emojiid import team_emoji_ids
from pytube import Search, YouTube
from lib.colors import colors
now = pd.Timestamp.now()

fastf1.Cache.enable_cache('cache/')

def quali_results(self,year,round):
    # embed setup
    message_embed = discord.Embed(title=f"Quali Results", description="").set_thumbnail(url='https://cdn.discordapp.com/attachments/884602392249770087/1059464532239581204/f1python128.png')
    message_embed.colour = colors.default
    
    # check if args are valid
    if (year == None):
        year = now.year
    if (round == None):
        # get latest completed session by starting from the end of calendar and going back towards beginning of season
        year_sched = fastf1.get_event_schedule(year,include_testing=False)
        round = (year_sched.shape[0]-1)
        sessionTime = year_sched.iloc[round].loc["Session4Date"].tz_convert('America/New_York')
        # print(sessionTime)
        while (now.tz_localize('America/New_York') < sessionTime):
            round -= 1
            sessionTime = year_sched.iloc[round].loc["Session4Date"].tz_convert('America/New_York')
        round += 1
        result_session = fastf1.get_session(year, round, 'Qualifying')
        # most recent session found, load it
        result_session.load()
    # round was given as number
    else:
        try:
            round_number = int(round)
            # inputs were valid, but the Qualifying hasnt happened yet
            if (now.tz_localize('America/New_York') < fastf1.get_event_schedule(year,include_testing=False).iloc[round_number].loc["Session4Date"].tz_convert('America/New_York')):
                message_embed.title = "Qualifying not found!"
                message_embed.description = "Round " + (str)(round_number) + " not found!"
                return message_embed
            # inputs were valid, get session
            result_session = fastf1.get_session(year, round_number, 'Qualifying')
            
        # round was given as string
        except Exception as e:
            try:
                # capitalize first letter of input to match dataframe value
                round_number = round.lower().title()
                # get schedule for the year
                df = fastf1.get_event_schedule(year,include_testing=False)
                # get start date of given Qualifying using panda dataframe fuckery
                Qualifyingstart_date = df.loc[df['Country'] == round_number,['Session4Date']].iloc[0].loc['Session4Date']

                # inputs were valid, but the Qualifying hasnt happened yet, return embed
                if (now.tz_localize('America/New_York') < Qualifyingstart_date.tz_convert('America/New_York')):
                    message_embed.title = "Qualifying not found!"
                    message_embed.description = f"Round {round_number} not found!"
                    return message_embed
                # inputs were valid, Qualifying has happened, get session
                result_session = fastf1.get_session(year, round_number, 'Qualifying')
            except:
                print(e)
                message_embed.description = "Invalid Input"
                return message_embed

    # load session
    result_session.load()
    resultsTable = result_session.results

    # test print
    # print(resultsTable)
    # print('\n\n')
    # print(resultsTable.columns.tolist())
    
    # get driver names and team emojis 
    driver_names = ""
    position_string = ""
    time_string = ""
    # status_string = ""
    if (resultsTable.empty):
        message_embed.description = "Session not found!"
        return message_embed
    for i in (resultsTable.DriverNumber.values):
        try:
            # print(resultsTable.loc[i,'TeamName'])
            driver_names += ((str)(self.bot.get_emoji(team_emoji_ids[resultsTable.loc[i,'TeamName']]))) + " " + resultsTable.loc[i,'FullName'] + "\n"
        except:
            driver_names += resultsTable.loc[i,'FullName'] + "\n"
        temp = (str)(resultsTable.loc[i,'Position'])
        position_string += temp[0:temp.index('.')] + "\n"
        # get best lap time from furthest session driver made it to (Q3? -> Q2? -> Q1)
        time = (str)(resultsTable.loc[i,'Q3'])
        q = 3
        if ('NaT' in time):
            time = (str)(resultsTable.loc[i,'Q2'])
            q = 2
            if ('NaT' in time):
                time = (str)(resultsTable.loc[i,'Q1'])
                q = 1
            
        # print(time)
        try:
            time = time[11:((str)(time)).index('.')+4]
        except:
            time = time[11:] + ".000"
        time = "Q" +(str)(q)+": " + time 
        time_string += time + "\n"
        
        
        # status_string += (str)(resultsTable.loc[i,'Status']) + "\n"

    # print(driver_names)
    raceName = result_session.event.EventName
    message_embed.title = f"{year} {raceName} Qualifying Results"

    s = Search((str)(year) + " " + raceName + " Qualifying")
    video_url = 'https://www.youtube.com/watch?v='
    t = (str)(s.results[0])
    video_url += (t[t.index('videoId=')+8:-1])
    thumbnail = YouTube(video_url).thumbnail_url

    message_embed.add_field(name = "Position", value = position_string,inline = True)
    message_embed.add_field(name = "Driver", value = driver_names,inline = True)
    message_embed.add_field(name = "Time", value = time_string,inline = True)
    message_embed.add_field(name = "Qualifying Highlights", value = video_url,inline = False)
    message_embed.set_image(url=thumbnail)    
    return message_embed
    

class Quali2(commands.Cog):

    def __init__(self, bot: commands.Bot):
        self.bot = bot
    @commands.Cog.listener()
    async def on_ready(self):
        print('Quali V2 cog loaded')  
    @app_commands.command(name = 'quali', description = 'Get results of a specific quali')
    @app_commands.describe(year = "Year")
    @app_commands.describe(round = "Round name or number (Australia or 3)")
    async def Quali2(self, interaction: discord.Interaction, year: typing.Optional[int], round: typing.Optional[str]):  
        await interaction.response.defer()
        loop = asyncio.get_running_loop()
        # run results query and build embed
        results_embed = await loop.run_in_executor(None, quali_results, self, year, round)
        results_embed.set_author(name='f1buddy',icon_url='https://raw.githubusercontent.com/F1-Buddy/f1buddy-python/main/botPics/f1pythonpfp.png')
        # send embed
        await interaction.followup.send(embed = results_embed)
        loop.close()

async def setup(bot):
    await bot.add_cog(Quali2(bot) # , guilds=[discord.Object(id=884602392249770084)]
                      )