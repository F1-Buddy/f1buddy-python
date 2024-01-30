import asyncio
import discord
import fastf1
import os
import typing
from fastf1 import plotting
from discord import app_commands
from discord.ext import commands
from matplotlib import pyplot as plt
from matplotlib.offsetbox import AnnotationBbox, OffsetImage
from lib.colors import colors
from lib.f1font import regular_font, bold_font
import pandas as pd
import traceback

fastf1.Cache.enable_cache('cache/')

# get current time
now = pd.Timestamp.now()
# set up pyplot
plotting.setup_mpl()
plt.grid(True, linestyle='--')
# setup embed
message_embed = discord.Embed(title="Lap Times", description="")
message_embed.colour = colors.default
message_embed.set_author(name='f1buddy',icon_url='https://raw.githubusercontent.com/F1-Buddy/f1buddy-python/main/botPics/f1pythonpfp.png')
message_embed.set_thumbnail(
url='https://cdn.discordapp.com/attachments/884602392249770087/1059464532239581204/f1python128.png')

def laptime_results(driver1: str, driver2: str, round:str, year: typing.Optional[int]):
    # fix for offseason
    # rewrite
    try:
        # year given is invalid
        try:
            year = int(year)
        except:
            year = now.year
        if (year > now.year | year < 2018):
            try:
                race = fastf1.get_session(now.year, round, 'R')
            except:
                race = fastf1.get_session(now.year, (int)(round), 'R')
            race.load(laps=False,telemetry=False,weather=False,messages=False)
            racename = '' + str(race.date.year)+' '+str(race.event.EventName)
        
        # use given year
        else:
            try:
                race = fastf1.get_session(year, round, 'R')
            except:
                race = fastf1.get_session(year, (int)(round), 'R')
            race.load(laps=True,telemetry=False,weather=False,messages=False)
            racename = '' + str(race.date.year)+' '+str(race.event.EventName)
        # check if graph already exists, if not create it
        if (not os.path.exists("cogs/plots/laptime/"+race.date.strftime('%Y-%m-%d_%I%M')+"_laptimes"+driver1+'vs'+driver2+'.png')) and (
            not os.path.exists("cogs/plots/laptime/"+race.date.strftime('%Y-%m-%d_%I%M')+"_laptimes"+driver2+'vs'+driver1+'.png')):
            
            # get driver data
            d1 = race.laps.pick_driver(driver1)
            d2 = race.laps.pick_driver(driver2)
            d1_number = d1.iloc[0].loc['DriverNumber']
            d2_number = d2.iloc[0].loc['DriverNumber']
            fig, ax = plt.subplots(figsize=(9, 6))
            fig.set_facecolor('black')
            ax.set_facecolor('black')
            # get driver color

            # if (year == now.year):
            #     print(driver1)
            #     d1_color = f1plt.driver_color(driver1)
            #     d2_color = f1plt.driver_color(driver2)
            # else:
            d1_color = f"#{race.results.loc[str(d1_number),'TeamColor']}"
            d2_color = f"#{race.results.loc[str(d2_number),'TeamColor']}"

            # if comparing teammates, change one drive color to white to be able to differentiate
            if d1_color == d2_color:
                d2_color = 'white'

            # plot laptimes
            ax.plot(d1['LapNumber'], d1['LapTime'], color=d1_color, label = driver1)
            ax.plot(d2['LapNumber'], d2['LapTime'], color=d2_color, label = driver2)
            # pyplot setup
            max_lap_count = max(max(d1['LapNumber']),max(d2['LapNumber']))
            ax.set_title(racename+ ' '+driver1+" vs "+driver2, fontproperties=bold_font)
            ax.set_xlabel(f"Lap Number (of {max_lap_count:.0f})", fontproperties=regular_font, labelpad=10)
            ax.set_ylabel("Lap Time", fontproperties=regular_font, labelpad=10)
            ax.set_xlim([0,max_lap_count])
            for label in ax.get_xticklabels() + ax.get_yticklabels():
                label.set_fontproperties(regular_font)
            ax.legend(loc="upper right", prop=bold_font)
            plt.rcParams['savefig.dpi'] = 300
            watermark_img = plt.imread('botPics/f1pythoncircular.png') # set directory for later use
            try:
                # add f1buddy pfp
                watermark_box = OffsetImage(watermark_img, zoom=0.1) 
                ab = AnnotationBbox(watermark_box, (-0.115,1.110), xycoords='axes fraction', frameon=False)
                ax.add_artist(ab)

                # add text next to it
                ax.text(-0.07,1.1, 'Made by F1Buddy Discord Bot', transform=ax.transAxes,
                        fontsize=10,fontproperties=bold_font)
            except Exception as e:
                print(e)
            # save plot
            plt.savefig("cogs/plots/laptime/"+race.date.strftime('%Y-%m-%d_%I%M')+"_laptimes"+driver1+'vs'+driver2+'.png')
            # reset plot just in case
            plt.clf()
            plt.cla()
            plt.close()
        # try to access the graph
        try:
            file = discord.File("cogs/plots/laptime/"+race.date.strftime('%Y-%m-%d_%I%M')+"_laptimes"+driver1+'vs'+driver2+'.png', filename="image.png")
            message_embed.description = '' + str(race.date.year)+' '+str(race.event.EventName)+ '\n' + driver1+" vs "+driver2
            message_embed.set_footer(text='')
            return file
        
        except Exception as e:
            # try to access the graph by switching driver1 and driver2 in filename
            try:
                file = discord.File("cogs/plots/laptime/"+race.date.strftime('%Y-%m-%d_%I%M')+"_laptimes"+driver2+'vs'+driver1+'.png', filename="image.png")
                message_embed.description = '' + str(race.date.year)+' '+str(race.event.EventName)+ '\n' + driver1+" vs "+driver2
                message_embed.set_footer(text='')
                print("Swapped drivers around and found a file")
                return file
            # file does not exist and could not be created
            except:
                message_embed.set_footer(text="Likely an unsupported input (year/round) was given \n *(2018+)*")
    # 
    except Exception as e:
        print(e)
        traceback.print_exc()
        message_embed.set_footer(text = e)



class Laptimes(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        print('Laptimes cog loaded')



    @app_commands.command(name='laptimes', description='Compare laptimes of two drivers in a race (2018 onwards)')
    
    # inputs
    @app_commands.describe(driver1='3 Letter Code for Driver 1')
    @app_commands.describe(driver2='3 Letter Code for Driver 2')
    @app_commands.describe(round='Round name or number (Australia or 3)')
    @app_commands.describe(year = "Year")
    
    # command
    async def laptimes(self, interaction: discord.Interaction, driver1: str, driver2: str, round:str, year: typing.Optional[int]):
        # defer reply for later
        await interaction.response.defer()
        # make sure inputs uppercase
        driver1 = driver1.upper()
        driver2 = driver2.upper()
        if driver1 == driver2:
            message_embed.description = "Use 2 different drivers!"
            await interaction.followup.send(embed=message_embed)
            return

        loop = asyncio.get_running_loop()
        # run results query and build embed
        file = await loop.run_in_executor(None, laptime_results, driver1, driver2, round, year)

        # send embed
        try:
            message_embed.set_image(url='attachment://image.png')
            await interaction.followup.send(embed=message_embed,file=file)
        except:
            message_embed.description += "Error Occured :("        
            message_embed.set_image(url='https://media.tenor.com/lxJgp-a8MrgAAAAd/laeppa-vika-half-life-alyx.gif')    
            await interaction.followup.send(embed=message_embed)
        loop.close()


async def setup(bot):
    await bot.add_cog(Laptimes(bot))
