import json
import traceback
import discord
import asyncio
import fastf1
import os
import typing
from discord import app_commands
from typing import Dict, List
from discord.ext import commands
from matplotlib import pyplot as plt
from matplotlib.offsetbox import AnnotationBbox, OffsetImage
from lib.colors import colors
import pandas as pd
import fastf1.plotting as f1plt
from lib.f1font import regular_font, bold_font
from matplotlib.ticker import (MultipleLocator)
import repeated.common as cm

# get current time
now = pd.Timestamp.now()

fastf1.Cache.enable_cache('cache/')

compound_colors: Dict[str, str] = {
    "SOFT": "#da291c",
    "MEDIUM": "#ffd12e",
    "HARD": "#f0f0ec",
    "INTERMEDIATE": "#43b02a",
    "WET": "#0067ad",
    "UNKNOWN": "#00ffff",
    "TEST-UNKNOWN": "#434649"
 }
compound_colors_2018: Dict[str, str] = {
    "SOFT": "#ffd12e", # yellow
    "MEDIUM": "#f0f0ec", # white
    "HARD": "#0096FF", # bright blue
    "INTERMEDIATE": "#43b02a",
    "WET": "#0067ad",
    "HYPERSOFT":"#FFC0CB", # pink
    "ULTRASOFT":"#BF40BF", # bright purple
    "SUPERSOFT":"#DA291C", # red
    "SUPERHARD":"#FFA500",
    "UNKNOWN": "#00ffff",
    "TEST-UNKNOWN": "#434649"
 }

# setup embed
message_embed = discord.Embed(title="Tire Strategy", description="")
message_embed.colour = colors.default
message_embed.set_author(name='f1buddy',icon_url='https://raw.githubusercontent.com/F1-Buddy/f1buddy-python/main/botPics/f1pythonpfp.png')
message_embed.set_thumbnail(
url='https://cdn.discordapp.com/attachments/884602392249770087/1059464532239581204/f1python128.png')

def tire_strategy(round, year):
    global compound_colors
    # pyplot setup
    f1plt.setup_mpl()
    fig, ax = plt.subplots(figsize=(10, 10))
    fig.set_facecolor('black')
    ax.set_facecolor('black')
    plt.xlabel("Lap", fontproperties=regular_font, fontsize=15, labelpad=15)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_visible(False)
    ax.tick_params(axis='y', length=0)
    plt.tight_layout()
    ax.yaxis.grid(False)
    ax.xaxis.grid(False)
    ax.minorticks_off() 
    plt.subplots_adjust(left=0.1,top = 0.89)
    # ax.set_facecolor('black')
    ax.invert_yaxis()
    ax.set_ylim([19.6, -0.6])
    # ax.set_yticks(range(1,21))
    ax.xaxis.set_major_locator(MultipleLocator(10))
    ax.xaxis.set_minor_locator(MultipleLocator(2))
    
    try:
        # year given is invalid
        if year is None:
            event_year = now.year
        else:
            if (year > now.year or year < 2018):
                event_year = now.year
                if (cm.currently_offseason()[0]) or (cm.latest_completed_index(now.year) == 0):
                    event_year = event_year - 1
            else:
                event_year = year
        try:
            event_round = int(round)
        except ValueError:
            event_round = round
        
        race = fastf1.get_session(event_year, event_round, 'R')
        race.load(laps=True,telemetry=False,weather=False,messages=False)
        laps = race.laps
        racename = '' + str(race.date.year)+' '+str(race.event.EventName)
        if event_year <= 2018:
            compound_colors = compound_colors_2018


        # check if graph already exists, if not create it
        message_embed.description = f"Tire strategies During the {racename}"
        file_exist = not os.path.exists("cogs/plots/strategy/"+race.date.strftime('%Y-%m-%d_%I%M')+"_strategy"+'.png')
        # file_exist = True
        if (file_exist):
            drivers = race.drivers
            drivers = [race.get_driver(driver)["Abbreviation"] for driver in drivers]

            stints = laps[["Driver", "Stint", "Compound", "LapNumber"]]
            stints = stints.groupby(["Driver", "Stint", "Compound"])
            stints = stints.count().reset_index()
            stints = stints.rename(columns={"LapNumber": "StintLength"})

            for driver in drivers:
                driver_stints = stints.loc[stints["Driver"] == driver]
                previous_stint_end = 0

                for idx, row in driver_stints.iterrows():
                    # each row contains the compound name and stint length
                    # we can use these information to draw horizontal bars
                    try:
                        plt.barh(
                            y=driver,
                            width=row["StintLength"],
                            left=previous_stint_end,
                            color=compound_colors[row["Compound"]],
                            edgecolor="black",
                            fill=True
                        )
                    except Exception as e:
                        print(e)

                    previous_stint_end += row["StintLength"]
            plt.rcParams['savefig.dpi'] = 300
            plt.title(f"{racename}\nTire Strategy", fontproperties=bold_font, fontsize=20)
            for label in ax.get_xticklabels():
                label.set_fontproperties(regular_font)
                label.set_fontsize(15)
            for label in ax.get_yticklabels():
                label.set_fontproperties(bold_font)
                label.set_fontsize(15)
            ax.tick_params(axis='y', pad=8)
            plt.subplots_adjust(top = 0.91)
            watermark_img = plt.imread('botPics/f1pythoncircular.png') # set directory for later use
            try:
                # add f1buddy pfp
                watermark_box = OffsetImage(watermark_img, zoom=0.1) 
                ab = AnnotationBbox(watermark_box, (-0.06,-0.06), xycoords='axes fraction', frameon=False)
                ax.add_artist(ab)
                # add text next to it
                ax.text(-0.025,-0.07, 'Made by F1Buddy Discord Bot', transform=ax.transAxes,
                        fontsize=13,fontproperties=bold_font)
            except Exception as e:
                print(e)
            # save plot
            plt.savefig("cogs/plots/strategy/"+race.date.strftime('%Y-%m-%d_%I%M')+"_strategy"+'.png')
            # plt.show()
            # clear plot
            plt.clf()
            plt.cla()
            plt.close()
        message_embed.title = f"{racename} Tire Strategy"
        if year==2018:
            message_embed.set_footer(text="2018 tire colors used",icon_url="https://cdn.discordapp.com/attachments/884602392249770087/1059464532239581204/f1python128.png")
        # try to access the graph
        try:
            file = discord.File("cogs/plots/strategy/"+race.date.strftime('%Y-%m-%d_%I%M')+"_strategy"+'.png', filename="image.png")
            return file
        
        except Exception as e:
            print(e)
            traceback_str = traceback.format_exc()
            print(traceback_str)
            message_embed.set_footer(text=e)
    # 
    except Exception as e:
        print(e)
        traceback_str = traceback.format_exc()
        print(traceback_str)
        message_embed.description = "Unknown error occured"
        message_embed.set_footer(text = e)

class Strategy(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        print('Strategy cog loaded')

    @app_commands.command(name='strategy', description='See tire strategies for the race')
    @app_commands.describe(round='Round name or number (Australia or 3)')
    @app_commands.describe(year = "Year (supports 2018 and after)")
    async def positions(self, interaction: discord.Interaction, round:str, year: typing.Optional[int]):
        # defer reply for later
        await interaction.response.defer()
        loop = asyncio.get_running_loop()
        # run results query and build embed
        file = await loop.run_in_executor(None, tire_strategy, round, year)

        # send embed
        try:
            message_embed.set_image(url='attachment://image.png')
            await interaction.followup.send(embed=message_embed,file=file)
        except:
            message_embed.set_image(url='https://media.tenor.com/lxJgp-a8MrgAAAAd/laeppa-vika-half-life-alyx.gif')
            message_embed.description = "Error Occured :("            
            await interaction.followup.send(embed=message_embed)
        loop.close()

# tire_strategy('Austria',2023)

async def setup(bot):
    await bot.add_cog(Strategy(bot))
