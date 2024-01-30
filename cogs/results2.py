import discord
import asyncio
import fastf1
import typing
import pandas as pd
from discord import app_commands
from discord.ext import commands
from lib.emojiid import team_emoji_ids
from pytube import Search
from lib.colors import colors
import repeated.embed as em

fastf1.Cache.enable_cache('cache/')

def results_result(self, year, round):
    now = pd.Timestamp.now().tz_localize('America/New_York')
    # embed setup
    message_embed = discord.Embed(title=f"Race Results", description="").set_thumbnail(url='https://cdn.discordapp.com/attachments/884602392249770087/1059464532239581204/f1python128.png')
    message_embed.colour = colors.default

    year_OoB = (year == None) or (year <= 1957) or (year >= now.year)
    if not year_OoB:
        year = year
    else:
        schedule = fastf1.get_event_schedule(now.year, include_testing=False)
        first_event_index = schedule.index[0]
        first_event_time = schedule.loc[first_event_index,'Session5DateUtc'].tz_localize("UTC")
        if now < first_event_time:
            year = now.year - 1

    # check if args are valid
    if (round == None):
        # get latest completed session by starting from the end of calendar and going back towards beginning of season
        year_sched = fastf1.get_event_schedule(year,include_testing=False)
        round = (year_sched.shape[0])
        sessionTime = year_sched.loc[round,"Session5Date"].tz_convert('America/New_York')
        # print(sessionTime)
        while (now < sessionTime):
            round -= 1
            sessionTime = year_sched.loc[round,"Session5Date"].tz_convert('America/New_York')
        result_session = fastf1.get_session(year, round, 'Race')
        # most recent session found, load it
        result_session.load(laps=False, telemetry=False, weather=False, messages=False)
    # round was given as number
    else:
        event_round = None
        try:
            event_round = int(round)
        except:
            event_round = round
        result_session = fastf1.get_session(year, event_round, 'Race')
        if (now - result_session.date.tz_localize('America/New_York')).total_seconds() < 0:
            message_embed.title = "Race hasn't happened yet!!"
            message_embed.set_image(url='https://media.tenor.com/lxJgp-a8MrgAAAAd/laeppa-vika-half-life-alyx.gif')
            message_embed.description = "Round \"" + (str)(event_round) + "\" not found!"
            return message_embed
        

    # load session
    result_session.load(laps=False, telemetry=False, weather=False, messages=False)
    resultsTable = result_session.results
    
    # strings for embed
    driver_names = ""
    position_string = ""
    points_string = ""
    # table is empty if race hasnt happened yet
    # unsure if necessary
    if (resultsTable.empty):
        message_embed.description = "Race not found!"
        message_embed.set_image(url='https://media.tenor.com/lxJgp-a8MrgAAAAd/laeppa-vika-half-life-alyx.gif')
        return message_embed
    # get each drivers finishing position/points and put them in the strings
    for i in (resultsTable.DriverNumber.values):
        # put team emoji before driver name if a matching emoji is found
        try:
            driver_names += ((str)(self.bot.get_emoji(team_emoji_ids[resultsTable.loc[i,'TeamName']]))) + " " + resultsTable.loc[i,'FullName'] + "\n"
        except:
            # emoji not found
            driver_names += resultsTable.loc[i,'FullName'] + "\n"
        # get driver position
        temp = (str)(resultsTable.loc[i,'Position'])
        # remove .0 from position
        temp_position = temp[0:temp.index('.')]
        # use medal emojis for top 3 positions
        match temp_position:
            case '1':
                temp_position = ':first_place:'
            case '2':
                temp_position = ':second_place:'
            case '3':
                temp_position = ':third_place:'
        position_string += temp_position + "\n"
        # get points and put in string
        temp_points = (str)(resultsTable.loc[i,'Points'])
        # if full points were awarded, remove .0 from points
        if temp_points[temp_points.index('.'):] == '.0':
            temp_points = temp_points[:temp_points.index('.')]
        points_string += temp_points + "\n"

    # get race name
    raceName = result_session.event.EventName
    message_embed.title = f"{year} {raceName} Race Results"

    # get link to race highlights youtube video
    s = Search((str)(year) + " " + raceName + " Highlights")
    video_url = 'https://www.youtube.com/watch?v='
    t = (str)(s.results[0])
    video_url += (t[t.index('videoId=')+8:-1])
    # thumbnail = YouTube(video_url).thumbnail_url

    # build embed and return it
    message_embed.add_field(name = "Position", value = position_string,inline = True)
    message_embed.add_field(name = "Driver", value = driver_names,inline = True)
    message_embed.add_field(name = "Points", value = points_string,inline = True)
    # message_embed.add_field(name = "Race Highlights", value = video_url,inline = False)
    # message_embed.set_image(url=thumbnail)
    return message_embed,video_url

class Results2(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
    @commands.Cog.listener()
    async def on_ready(self):
        print('Results V2 cog loaded')  
    @app_commands.command(name = 'results', description = 'Get results of a specific race')
    @app_commands.describe(year = "Year")
    @app_commands.describe(round = "Round name or number (Australia or 3)")
    
    async def Results2(self, interaction: discord.Interaction, year: typing.Optional[int], round: typing.Optional[str]):  
        await interaction.response.defer()
        loop = asyncio.get_running_loop()
        # run results query and build embed
        results_embed,video_url = await loop.run_in_executor(None, results_result, self, year, round)
        results_embed.set_author(name='f1buddy',icon_url='https://raw.githubusercontent.com/F1-Buddy/f1buddy-python/main/botPics/f1pythonpfp.png')
        # send embed
        await interaction.followup.send(embed = results_embed)
        await interaction.followup.send(video_url)
        loop.close()

async def setup(bot):
    await bot.add_cog(Results2(bot) # , guilds=[discord.Object(id=884602392249770084)]
                      )