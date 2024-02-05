import discord
import asyncio
import fastf1
import os
import traceback
import typing
from discord import app_commands
from discord.ext import commands
from matplotlib import pyplot as plt
from matplotlib.offsetbox import AnnotationBbox, OffsetImage
from numpy import mean
from lib.f1font import regular_font, bold_font
import matplotlib.patches as mpatches
import matplotlib
# from matplotlib.ticker import (MultipleLocator)
matplotlib.use('agg')
# from lib.colors import colors
import repeated.embed as em
import pandas as pd
import fastf1.plotting as f1plt

# get current time
now = pd.Timestamp.now()

fastf1.Cache.enable_cache('cache/')

def td_to_laptime(td):
    td_microseconds = td.microseconds
    td_seconds = td.seconds
    td_minutes = td_seconds // 60
    td_seconds = str(td_seconds % 60).zfill(2)
    td_thousandths = str(td_microseconds)[:-3].zfill(3)
    return f"{td_minutes}:{td_seconds}.{td_thousandths}"

def plot_telem(driver_list, lap_number: typing.Optional[int], event_round, event_year: typing.Optional[int], sessiontype, file_path):
    # driver data
    drivers_list = sorted(driver_list)
    driver_allLaps = []
    driver_numbers = []
    driver_names = []
    driver_targetlaps = []
    driver_telemetry = []
    driver_lapTimes = []

    # for plotting
    driver_speeds = []
    driver_throttle = []
    driver_brakes = []
    driver_indexList = []
    driver_colors = []
    driver_patches = []

    f1plt.setup_mpl()
    fig, ax = plt.subplots(3, figsize=(13,9))
    if lap_number == None:
        fig.suptitle('Fastest Lap Telemetry',fontproperties=bold_font,size=20,x=0.53)
    else:
        fig.suptitle(f'Lap {lap_number} Telemetry',fontproperties=bold_font,size=20,x=0.53)
    fig.set_facecolor('black')
    plt.xlabel('Lap Percentage',fontproperties=bold_font, labelpad=10)
    ax[1].set_ylim([0, 105])
    ax[2].set_ylim([0,1.1])
    ax[0].set_facecolor('black')    
    ax[1].set_facecolor('black')    
    ax[2].set_facecolor('black')    

    plt.subplots_adjust(left = 0.07, right = 0.98, top = 0.89, hspace=0.8)

    race = fastf1.get_session(event_year, event_round, sessiontype.value)
    race.load(laps=True,telemetry=True,weather=False,messages=False)
    f = open(file_path[:-3]+'txt', 'w')
    f.write(f'{str(race)}\n')
    f.close()
    
    for i in range(len(drivers_list)):
        # data
        driver_allLaps.append(race.laps.pick_driver(drivers_list[i]))
        driver_numbers.append(driver_allLaps[i].iloc[0].loc['DriverNumber'])
        driver_names.append(drivers_list[i])
        if lap_number == None:
            driver_targetlaps.append(driver_allLaps[i].pick_fastest())
            driver_lapTimes.append(driver_targetlaps[i]["LapTime"])
        else:
            driver_targetlaps.append(driver_allLaps[i].pick_lap(int(lap_number)))
            driver_lapTimes.append(driver_targetlaps[i].loc[driver_targetlaps[i].index[0],"LapTime"])
        # plotting data
        driver_telemetry.append(driver_targetlaps[i].get_telemetry())
        driver_speeds.append(driver_telemetry[i]['Speed'].to_list())
        driver_throttle.append(driver_telemetry[i]['Throttle'].to_list())
        driver_brakes.append(driver_telemetry[i]['Brake'].to_list())
        driver_indexList.append((driver_telemetry[i].index/max(driver_telemetry[i].index)).to_list())
        if not f"#{race.results.loc[str(driver_numbers[i]),'TeamColor']}"in driver_colors:
            driver_colors.append(f"#{race.results.loc[str(driver_numbers[i]),'TeamColor']}")
        else:
            driver_colors.append('white')
        driver_patches.append(mpatches.Patch(color=driver_colors[i], label=driver_names[i]))
        # plotting
        ax[0].plot(driver_indexList[i],driver_speeds[i],color=driver_colors[i])
        ax[0].axhline(mean(driver_speeds[i]), linestyle='--', label=f'D{i} avg speed', c=driver_colors[i], lw = 0.5)
        ax[1].plot(driver_indexList[i],driver_throttle[i],color=driver_colors[i])
        ax[2].plot(driver_indexList[i],driver_brakes[i],color=driver_colors[i])
        f = open(file_path[:-3]+'txt', 'a')
        f.write(f"{driver_names[i]}: {td_to_laptime(driver_lapTimes[i])}\n")
        f.close()
        
    # plot setup
    speeds = []
    for df in driver_telemetry:
        speeds.append(df["Speed"].max())
    max_speed = 10 + max(speeds)
    # if len(drivers_list) == 1:
    #     max_speed = max(driver_telemetry[0]['Speed'])+10
    # else:
    #     max_speed = max(max(driver_telemetry[0]['Speed']),max(driver_telemetry[1]['Speed']))+10
    ax[0].set_ylim([0, max_speed])

    ax[0].set_ylabel('Speed (km/h)',fontproperties=regular_font, labelpad=8)
    ax[0].set_title("Speed", fontproperties=bold_font, fontsize=15)

    ax[1].set_ylabel('Throttle %',fontproperties=regular_font, labelpad=8)
    ax[1].set_title("Throttle", fontproperties=bold_font, fontsize=15)

    ax[2].set_yticks(ticks = [0,1],labels= ['Off','On'])
    ax[2].set_title("Brake", fontproperties=bold_font, fontsize=15)

    for i in range(3):
        ax[i].xaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(xmax=1, decimals=0))
        ax[i].xaxis.set_major_locator(matplotlib.ticker.MultipleLocator(base=0.1))
        ax[i].set_xlim([0, 1])
        for label in ax[i].get_xticklabels():
            label.set_fontproperties(regular_font)
        for label in ax[i].get_yticklabels():
            label.set_fontproperties(bold_font)
    plt.grid(visible=False, which='both')
    plt.legend(handles=driver_patches,bbox_to_anchor=(1.01, 5.2),loc='upper right', prop=regular_font)
    # watermark
    watermark_img = plt.imread('botPics/f1pythoncircular.png')
    watermark_box = OffsetImage(watermark_img, zoom=0.125) 
    ab = AnnotationBbox(watermark_box, (-0.045,1.35), xycoords='axes fraction', frameon=False)
    ax[0].add_artist(ab)
    ax[0].text(-0.015,1.3, 'Made by F1Buddy Discord Bot', transform=ax[0].transAxes,
            fontsize=13,fontproperties=bold_font)
    plt.rcParams['savefig.dpi'] = 300
    plt.savefig(file_path)
    

def get_embed_and_image(driver1, driver2, year, round, lap_number, sessiontype):
    
    if (year > now.year) | (year < 2018):
        return em.ErrorEmbed(error_message="Enter a valid year from 2018 to now"), None
    else:
        event_year = year
    try:
        event_round = int(round)
    except:
        event_round = round
    driver_list = []

    driver_list.append(driver1.upper())
    if driver2 != None:
        driver_list.append(driver2.upper())
    driver_list = sorted(driver_list)
    
    if lap_number == None:
        title = f"Fastest Lap {sessiontype.name.capitalize()} Telemetry"
    else:
        title = f"Lap {lap_number} Telemetry"
    try:
        race = fastf1.get_session(event_year, event_round, sessiontype.value)
    except Exception as e:
        # catch bad round
        traceback.print_exc()
        return em.ErrorEmbed(error_message=f"{type(e)}: {str(e)}\nError getting round, likely bad input given"), None
    try:
        round_num = str(race)
        round_num = (round_num[round_num.index('Round')+6:round_num.index(':')])
        
        folder_path = f'./cogs/plots/telemetry/{event_year}/{round_num}/{sessiontype.name}/'
        file_name = f'{lap_number}_{''.join(driver_list)}.png'
        file_path = f'./cogs/plots/telemetry/{{event_year}}/{{round_num}}/{{sessiontype.name}}/{file_name}'
        if not (os.path.exists(file_path)):
            if not os.path.exists(folder_path):
                os.makedirs(folder_path)
            # catch any drawing errors
            try:
                plot_telem(driver_list, lap_number, event_round, event_year, sessiontype, file_path)
            except Exception as e:
                return em.ErrorEmbed(error_message=str(e)),None
        file = discord.File(file_path,filename="image.png")
        description = open(file_path[:-3]+'txt').read()
        return em.Embed(title=title,description=description,image_url='attachment://image.png'), file   
    except Exception as e:
        traceback.print_exc()
        return em.ErrorEmbed(error_message=str(e)), None
class Telemetry(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        print('Telemetry cog loaded')

    @app_commands.command(name='telemetry', description='Compare telemetry between 2 drivers on a specific lap, leave blank for respective fastest laps')
    @app_commands.describe(sessiontype='Choose between Race or Qualifying')
    @app_commands.choices(sessiontype=[
        app_commands.Choice(name="FP1", value="FP1"),
        app_commands.Choice(name="FP2", value="FP2"),
        app_commands.Choice(name="FP3", value="FP3"),
        app_commands.Choice(name="Qualifying", value="Q"),
        app_commands.Choice(name="Race", value="R"),
        ])
    # inputs
    @app_commands.describe(driver1='3 Letter Code for Driver 1')
    @app_commands.describe(driver2='3 Letter Code for Driver 2')
    @app_commands.describe(round='Round name or number (Australia or 3)')
    @app_commands.describe(year = "Year")
    
    # command
    async def telemetry(self, interaction: discord.Interaction, driver1: str, driver2: typing.Optional[str], lap_number: typing.Optional[int], round:str, year: int, sessiontype: app_commands.Choice[str]):
        # defer reply for later
        await interaction.response.defer()
            
        driver1 = driver1.upper()
        if not (driver2 == None):
            driver2 = driver2.upper()
            if driver1 == driver2:
                await interaction.followup.send(embed=em.ErrorEmbed(error_message="Use 2 different drivers!").embed)
                return
        loop = asyncio.get_running_loop()
        # run results query and build embed
        dc_embed,file = await loop.run_in_executor(None, get_embed_and_image, driver1, driver2, year, round, lap_number, sessiontype)
        # send embed
        if file != None:
            await interaction.followup.send(embed=dc_embed.embed,file=file)
        else:
            await interaction.followup.send(embed=dc_embed.embed)
        loop.close()


async def setup(bot):
    await bot.add_cog(Telemetry(bot))

# telemetry_results("VER","HAM",'hungary',2023,'race')