import discord
import asyncio
import fastf1
import os
import typing
from discord import app_commands
from discord.ext import commands
from matplotlib import pyplot as plt
from lib.f1font import regular_font, bold_font
import matplotlib
matplotlib.use('agg')
from lib.colors import colors
import pandas as pd
import fastf1.plotting as f1plt
from matplotlib.ticker import (MultipleLocator)

fastf1.Cache.enable_cache('cache/')

# setup embed
message_embed = discord.Embed(title="Driver Positions", description="")
message_embed.colour = colors.default
message_embed.set_author(name='f1buddy',icon_url='https://raw.githubusercontent.com/F1-Buddy/f1buddy-python/main/botPics/f1pythonpfp.png')
message_embed.set_thumbnail(
url='https://cdn.discordapp.com/attachments/884602392249770087/1059464532239581204/f1python128.png')

def positions_result(round, year):
    # pyplot setup
    f1plt.setup_mpl()
    f1plt.setup_mpl(misc_mpl_mods=False)
    fig, ax = plt.subplots(figsize=(8.0, 4.9))
    plt.ylabel("Position",fontproperties=regular_font, labelpad=10)
    plt.xlabel("Lap",fontproperties=regular_font, labelpad=10)
    plt.tight_layout()
    plt.subplots_adjust(right=0.85,top = 0.89)
    fig.set_facecolor('black')
    ax.set_facecolor('black')
    ax.set_ylim([21, 0])
    ax.set_yticks(range(1,21))
    # get current time
    now = pd.Timestamp.now()

    try:
        # year given is invalid
        if year == None:
            event_year = now.year
        else:
            if (year > now.year | year < 2018):
                event_year = now.year
            else:
                event_year = year
        try:
            event_round = int(round)
        except ValueError:
            event_round = round
        race = fastf1.get_session(event_year, event_round, 'R')
        race.load(laps=True,telemetry=False,weather=False,messages=False)
        racename = '' + str(race.date.year)+' '+str(race.event.EventName)

        # check if graph already exists, if not create it
        message_embed.description = racename
        if (not os.path.exists("cogs/plots/positions/"+race.date.strftime('%Y-%m-%d_%I%M')+"_positions"+'.png')):

            for driver in race.drivers:
                driver_laps = race.laps.pick_driver(driver)
                try:
                    driver_name = driver_laps["Driver"].iloc[0]
                    # if current year, then use driver_color method, else use teamcolor
                    if (year == now.year):
                        driver_color = f1plt.driver_color(driver_name)
                    else:
                        driver_color = f"#{race.results.loc[driver,'TeamColor']}"
                    # try to plot the driver's line
                    try:
                        plt.plot(driver_laps["LapNumber"],driver_laps["Position"], color = driver_color, label = driver_name)
                    except:
                        # try to plot the line using white as color
                        try:
                            plt.plot(driver_laps["LapNumber"],driver_laps["Position"], color = 'white', label = driver_name)
                        # absolute and utter failure
                        except Exception as e:
                            print(e)
                except:
                    # mazepin has no data
                    print("no info for this driver")

            # pyplot setup
            ax.legend(bbox_to_anchor=(1.0, 1.02), fontsize=9.2, prop=bold_font)
            ax.minorticks_off()
            ax.xaxis.set_major_locator(MultipleLocator(5))
            ax.xaxis.set_minor_locator(MultipleLocator(1))
            
            plt.title('Position Changes During '+racename, fontproperties=bold_font)
            plt.grid(visible=False, which='both')
            plt.rcParams['savefig.dpi'] = 300
            for label in ax.get_xticklabels() + ax.get_yticklabels():
                label.set_fontproperties(regular_font)
            # save plot
            plt.savefig("cogs/plots/positions/"+race.date.strftime('%Y-%m-%d_%I%M')+"_positions"+'.png')
            # clear plot
            plt.clf()
            plt.cla()
            plt.close()
        # try to access the graph
        try:
            file = discord.File("cogs/plots/positions/"+race.date.strftime('%Y-%m-%d_%I%M')+"_positions"+'.png', filename="image.png")
            message_embed.set_footer(text="")
            return file
        
        except Exception as e:
            print(e)
            message_embed.set_footer(text=e)
    # 
    except Exception as e:
        print(e)
        message_embed.set_footer(text = e)

class Positions(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        print('Positions cog loaded')

    @app_commands.command(name='positions', description='See driver position changes over the race')
    @app_commands.describe(round='Round name or number (Australia or 3)')
    @app_commands.describe(year = "Year")
    async def positions(self, interaction: discord.Interaction, round:str, year: typing.Optional[int]):
        # defer reply for later
        await interaction.response.defer()
        loop = asyncio.get_running_loop()
        # run results query and build embed
        file = await loop.run_in_executor(None, positions_result, round, year)

        # send embed
        try:
            message_embed.set_image(url='attachment://image.png')
            await interaction.followup.send(embed=message_embed,file=file)
        except:
            message_embed.set_image(url='https://media.tenor.com/lxJgp-a8MrgAAAAd/laeppa-vika-half-life-alyx.gif')
            message_embed.description = "Error Occured :("            
            await interaction.followup.send(embed=message_embed)
        loop.close()


async def setup(bot):
    await bot.add_cog(Positions(bot))
