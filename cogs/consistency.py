import asyncio
import datetime
import os
import traceback
import typing
import fastf1
from matplotlib import patches, pyplot as plt, ticker
import pandas as pd
# from lib.drivernames import driver_names
from lib.f1font import regular_font, bold_font
from lib.colors import colors
import discord
from discord import app_commands
from discord.ext import commands
# import traceback
lap_colors = []
now = pd.Timestamp.now()
fastf1.Cache.enable_cache('cache/')

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
        # result_session.load()
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
    # print(result_session.results) 
    
    try:
        specified_driver = driver
        driver_laps = result_session.laps.pick_driver(driver)
        mean_lap_time = driver_laps[(driver_laps['LapNumber'] != 1)]
        mean_lap_time = mean_lap_time[(driver_laps['LapTime'].dt.total_seconds() <= (mean_lap_time['LapTime'].mean().total_seconds() + 13))]
        mean_lap_time = mean_lap_time['LapTime'].mean().total_seconds()
    except Exception as e:
        traceback.print_exc()
    # print(mean_lap_time)
    try:
        outlier_laps = result_session.laps.pick_driver(driver)
        # condition1 = outlier_laps['PitInTime'].notnull()
        condition2 = outlier_laps['PitOutTime'].notnull()
        condition3 = outlier_laps['LapTime'].dt.total_seconds() >= (mean_lap_time + 10)
        # outlier_laps = outlier_laps[(outlier_laps['LapTime'].dt.total_seconds() >= (outlier_laps['LapTime'].mean().total_seconds() + 13))]
        outlier_laps = outlier_laps[ condition2 | condition3]
        # print(outlier_laps)
    except:
        traceback.print_exc()
    try:
        std_driver_laps = driver_laps[(driver_laps['LapNumber'] != 1)]
        std_driver_laps = std_driver_laps[(driver_laps['LapTime'].dt.total_seconds() <= mean_lap_time + 13)]
        std_lap_time = std_driver_laps['LapTime'].std()
        std_lap_time = (datetime.datetime.min + std_lap_time).time().strftime('%M:%S.%f')[:-3]
        # print(std_driver_laps)
    except Exception as e:
        print(e)
        
    filename = f"cogs/plots/consistency/consistency{result_session.date.strftime('%Y-%m-%d_%I%M')}_{specified_driver}.png"
    if not os.path.exists(filename):
        fig, ax = plt.subplots(figsize=(9,6))
        # plt.subplots_adjust(left=0.1)
        # set blackground
        ax.set_facecolor('black')    
        fig.set_facecolor('black')
    
        # print(driver_laps.index)
        # lowest_laptime = float('99999999') 
        # lowest_lap_index = -1

        for i in driver_laps.index:
            try:
                curr_laptime = driver_laps.loc[i, 'LapTime'].total_seconds()
                
                # if curr_laptime < lowest_laptime:
                #     lowest_laptime = curr_laptime
                #     lowest_lap_index = i
            
                if curr_laptime <= mean_lap_time:
                    point_color = "#00ff00"
                else:
                    point_color = "#ffaf00"
                plt.scatter(driver_laps.loc[i, 'LapNumber'], curr_laptime, c=point_color)
            except Exception as e:
                print(f"Error {e}")

        min_lap_time = min(driver_laps['LapTime'])
        min_lap_df = driver_laps[driver_laps['LapTime'] == min_lap_time]
        min_lap_number = min_lap_df.loc[min_lap_df.index[0],'LapNumber']

        # if lowest_lap_index != -1:
        plt.scatter(min_lap_number, min_lap_time.total_seconds(), c="#B138DD")
        plt.axhline(mean_lap_time, linestyle='--', label='Mean Lap Time', c="#969696")
        for i in outlier_laps.index:
            try:
                curr_laptime = outlier_laps.loc[i, 'LapTime'].total_seconds()
                plt.scatter(outlier_laps.loc[i, 'LapNumber'], curr_laptime, c="#F91536")
            except Exception as e:
                traceback.print_exc()
        
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
        slow_patch = patches.Patch(color="#ffaf00", label="Slower than AVG")
        quick_patch = patches.Patch(color="#00ff00", label="Quicker than AVG")
        mean_patch = patches.Patch(color="#969696", label="Average Lap Time")
        outlier_patch = patches.Patch(color="#F91536", label="Outlier")
        quickest_patch = patches.Patch(color="#B138DD", label="Fastest Lap")
        plt.legend(handles=[mean_patch, quickest_patch, quick_patch, slow_patch, outlier_patch], prop=bold_font,bbox_to_anchor=(1.3,1))
        # plt.legend()
        plt.savefig(f"cogs/plots/consistency/consistency{result_session.date.strftime('%Y-%m-%d_%I%M')}_{specified_driver}.png",bbox_inches='tight') # save plot
    
    consistency_embed.title = f"{driver} Laptime Consistency"
    try:
        consistency_embed.description = f"{raceName}\n\u03c3 = {std_lap_time}"
        consistency_embed.set_footer(text="Standard deviation (\u03c3) & mean calculated excluding outliers",icon_url="https://cdn.discordapp.com/attachments/884602392249770087/1059464532239581204/f1python128.png")

    except:
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