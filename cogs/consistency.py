import asyncio
import typing
import fastf1
from matplotlib import pyplot as plt, ticker
import pandas as pd
# from lib.drivernames import driver_names
from lib.f1font import regular_font, bold_font
from lib.colors import colors
import discord
from discord import app_commands
from discord.ext import commands
import traceback
lap_colors = []
now = pd.Timestamp.now()

# fuck this function we do it later
# def convert_to_code(driver):
#     if driver in driver_names.values():
#         return driver
#     driver_code = driver_names.get(driver)
#     if driver_code is None:
#         raise ValueError(f"Unknown driver: {driver}")
#     return driver_code

consistency_embed = discord.Embed(title="Laptime Consistency", description="")

def laptime_consistency(driver, year, round):
    # print(f"year = {year}")
    # print(f"round = {round}")
    # print(f"type(year) = {type(year)}")
    # print(f"type(round) = {type(round)}")
    # check if args are valid
    if (year == None):
        year = now.year
    elif (year > now.year):
        year = now.year
    if (round == None):
        # get latest completed session by starting from the end of calendar and going back towards beginning of season
        year_sched = fastf1.get_event_schedule(year,include_testing=False)
        round = (year_sched.shape[0])
        sessionTime = year_sched.loc[round,"Session5Date"].tz_convert('America/New_York')
        # print(sessionTime)
        while (now.tz_localize('America/New_York') < sessionTime):
            round -= 1
            sessionTime = year_sched.loc[round,"Session5Date"].tz_convert('America/New_York')
        result_session = fastf1.get_session(year, round, 'Race')
        # most recent session found, load it
        result_session.load()
    # round was given as number
    else:
        event_round = None
        try:
            event_round = int(round)
        except:
            event_round = round
        result_session = fastf1.get_session(year, event_round, 'Race')
        if (now.tz_localize('America/New_York') - result_session.date.tz_localize('America/New_York')).total_seconds() < 0:
            consistency_embed.title = "Race hasn't happened yet!!"
            consistency_embed.set_image(url='https://media.tenor.com/lxJgp-a8MrgAAAAd/laeppa-vika-half-life-alyx.gif')
            consistency_embed.description = "Round \"" + (str)(event_round) + "\" not found!"
            return consistency_embed
        
    raceName = f"{year} {result_session.event.EventName}"
    # load session
    result_session.load()
    # this load may be repetetive, unsure
    

    specified_driver = driver

    driver_laps = result_session.laps.pick_driver(driver)

    mean_lap_time = driver_laps['LapTime'].mean().total_seconds()


    fig, ax = plt.subplots()

    # print(driver_laps.index)
    for i in driver_laps.index:
        try:
            point_color = ""
            curr_laptime = driver_laps.loc[i,'LapTime'].total_seconds()
            if curr_laptime <= mean_lap_time:
                point_color = "green"
            else:
                point_color = "red"
            plt.scatter(driver_laps.loc[i,'LapNumber'], driver_laps.loc[i,'LapTime'].total_seconds(), c = point_color)
        except Exception as e:
            print(f"Error {e}")

        
    plt.axhline(mean_lap_time, color='red', linestyle='--', label='Mean Lap Time', c="#969696")
=======
lap_colors = []

def convert_to_code(driver):
    if driver in driver_names.values():
        return driver
    driver_code = driver_names.get(driver)
    if driver_code is None:
        raise ValueError(f"Unknown driver: {driver}")
    return driver_code

def laptime_consistency(driver):
    driver_code = convert_to_code(driver)
    print(driver_code)
    session = fastf1.get_session(2023, 1, 'R')
    session.load(telemetry=True, laps=True)
    

    specified_driver = 'ALO'
    driver_laps = session.laps.pick_driver(specified_driver)
    print(driver_laps['LapTime'])
    print(driver_laps['LapTime'].dt.total_seconds())
    print(driver_laps['LapNumber'])
    final_lap_number = driver_laps['LapNumber'].max()
    mean_lap_time = driver_laps['LapTime'].mean().total_seconds()
    std_lap_time = driver_laps['LapTime'].std()

    # for lap_time in driver_laps['LapTime'].dt.total_seconds():
    #     if lap_time > mean_lap_time:
    #         lap_colors.append('blue')  
    #     else:
    #         lap_colors.append('green')  

    fig, ax = plt.subplots()
    # fig.set_facecolor('black')
    # ax.set_facecolor('black')
    try:
        plt.scatter(driver_laps['LapNumber'], driver_laps['LapTime'].dt.total_seconds())
    except Exception as e:
        print(f"Error {e}")
        # ax.plot(driver_laps['LapNumber'], driver_laps['LapTime'].dt.total_seconds(), color='blue', label=specified_driver)
        
    ax.axhline(mean_lap_time, color='red', linestyle='--', label='Mean Lap Time')
    # ax.plot(driver_laps['LapNumber'], driver_laps['LapTime'].dt.total_seconds(), color='blue', label=specified_driver)

    y_ticks = ax.get_yticks()
    converted_labels = []
    for tick in y_ticks:
        minutes = int(tick // 60)
        seconds = int(tick % 60)
        converted_labels.append("{:02d}:{:02d}".format(minutes, seconds))
    
    ax.set_yticklabels(converted_labels)
    ax.set_title(f"{specified_driver} Laptime Consistency during \n{raceName}", fontproperties=bold_font)
    ax.set_xlabel("Lap Number", fontproperties=regular_font, labelpad=10)
    ax.set_ylabel("Lap Time", fontproperties=regular_font, labelpad=10)
    for label in ax.get_xticklabels() + ax.get_yticklabels():
        label.set_fontproperties(regular_font)
    plt.rcParams['savefig.dpi'] = 300
    
    plt.savefig(f"cogs/plots/consistency/consistency{result_session.date.strftime('%Y-%m-%d_%I%M')}_{specified_driver}.png") # save plot
    
    consistency_embed.title = f"{driver} Laptime Consistency"
    consistency_embed.description = f"{raceName}"

    consistency_embed.colour = colors.default
    consistency_embed.set_author(name='f1buddy',icon_url='https://raw.githubusercontent.com/F1-Buddy/f1buddy-python/main/botPics/f1pythonpfp.png')
    consistency_embed.set_thumbnail(url='https://cdn.discordapp.com/attachments/884602392249770087/1059464532239581204/f1python128.png')
    try:
        file = discord.File(f"cogs/plots/consistency/consistency{result_session.date.strftime('%Y-%m-%d_%I%M')}_{specified_driver}.png", filename="image.png")
    except Exception as e:
        print(e)
        consistency_embed.set_footer(text=e)
        
    return consistency_embed, file

class Consistency(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
    @commands.Cog.listener()
    async def on_ready(self):
        print('Laptime consistency cog loaded')
        
    @app_commands.command(name='consistency', description='Plot driver laptime consistency')
    @app_commands.describe(driver = "Driver name/code")
    @app_commands.describe(round='Round name or number (Australia or 3)')
    @app_commands.describe(year = "Year")
    async def consistency(self, interaction: discord.Interaction, driver:str, round: typing.Optional[str], year: typing.Optional[int]):
        await interaction.response.defer()
        loop = asyncio.get_running_loop()
        try:
            consistency_embed, file = await loop.run_in_executor(None, laptime_consistency, driver.upper(),year,round)
            consistency_embed.set_image(url='attachment://image.png')
            await interaction.followup.send(embed=consistency_embed, file=file)
        except Exception as e:
            consistency_embed.set_image(url='https://media.tenor.com/lxJgp-a8MrgAAAAd/laeppa-vika-half-life-alyx.gif')
            consistency_embed.description = f"Error Occured :( {e}"            
            await interaction.followup.send(embed=consistency_embed)
        loop.close()

async def setup(bot):
    await bot.add_cog(Consistency(bot))