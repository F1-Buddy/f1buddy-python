import discord
import asyncio
import fastf1
import os
import traceback
import typing
from discord import app_commands
from discord.ext import commands
from matplotlib import pyplot as plt
import matplotlib.patches as mpatches
import matplotlib
from matplotlib.ticker import (MultipleLocator, AutoMinorLocator)
matplotlib.use('agg')
from lib.colors import colors
import pandas as pd
import fastf1.plotting as f1plt


# get current time
now = pd.Timestamp.now()

fastf1.Cache.enable_cache('cache/')

# setup embed
message_embed = discord.Embed(title="Track Dominance", description="")
message_embed.colour = colors.default
message_embed.set_author(name='f1buddy',icon_url='https://raw.githubusercontent.com/F1-Buddy/f1buddy-python/main/botPics/f1pythonpfp.png')
message_embed.set_thumbnail(
url='https://cdn.discordapp.com/attachments/884602392249770087/1059464532239581204/f1python128.png')


def speed_results(driver1: str, driver2: str, round:str, year: typing.Optional[int], sessiontype):
    message_embed.description = ""
    message_embed.title = f"Track Dominance during {sessiontype.name.capitalize()}"
    message_embed.set_footer(text="")
    # pyplot setup
    f1plt.setup_mpl()
    fig, ax = plt.subplots()
    ax.axis('equal')
    ax.axis('off')
    try:
        # year given is invalid
        try:
            year = int(year)
        except:
            year = now.year
        if (year > now.year | year < 2018):
            race = fastf1.get_session(now.year, round, sessiontype.value)
        
        # use given year
        else:
            race = fastf1.get_session(year, round, sessiontype.value)
        # check if graph already exists, if not create it
        race.load()
        message_embed.description = race.event.EventName
        d1_laps = race.laps.pick_driver(driver1)
        d1_fastest = d1_laps.pick_fastest()
        d1_number = d1_laps.iloc[0].loc['DriverNumber']
        d1_name = driver1
        
        d2_laps = race.laps.pick_driver(driver2)
        d2_fastest = d2_laps.pick_fastest()
        d2_number = d2_laps.iloc[0].loc['DriverNumber']
        d2_name = driver2
        
        if (not os.path.exists("cogs/plots/speed/"+race.date.strftime('%Y-%m-%d_%I%M')+f"_{sessiontype.name}_"+"_speed_"+d1_name+'vs'+d2_name+'.png')) and (
            not os.path.exists("cogs/plots/speed/"+race.date.strftime('%Y-%m-%d_%I%M')+f"_{sessiontype.name}_"+"_speed_"+d2_name+'vs'+d1_name+'.png')):
            try:
                d1_telemetry_data = d1_fastest.get_telemetry()
                d2_telemetry_data = d2_fastest.get_telemetry()
                # d1_lap_data = d1_laps.pick_fastest().get_pos_data()
                # d1_car_data = d1_laps.pick_fastest().get_car_data()
                # d2_lap_data = d2_laps.pick_fastest().get_pos_data()
                # d2_car_data = d2_laps.pick_fastest().get_car_data()

                for c in d1_telemetry_data.index:
                    try:
                        # get driver color
                        if (year == now.year):
                            d1_color = f1plt.driver_color(d1_name)
                            d2_color = f1plt.driver_color(d2_name)
                        else:
                            d1_color = f"#{race.results.loc[str(d1_number),'TeamColor']}"
                            d2_color = f"#{race.results.loc[str(d2_number),'TeamColor']}"
                        if d1_color == d2_color:
                            d2_color = 'white'
                        if (d1_telemetry_data.loc[c,"Speed"] >= d2_telemetry_data.loc[c,"Speed"]):
                            # print(f"in {c} {d1_name} is faster than {d2_name}")
                            # print(str(d1_telemetry_data.loc[c,"Speed"]) + " > " + str(d2_telemetry_data.loc[c,"Speed"]))
                            plt.scatter(d1_telemetry_data.loc[c,"X"],d1_telemetry_data.loc[c,"Y"],color=d1_color,s=2,label=d1_name)
                        elif (d1_telemetry_data.loc[c,"Speed"] < d2_telemetry_data.loc[c,"Speed"]):
                            # print(f"in {c} {d2_name} is faster than {d1_name}")
                            # print(str(d1_telemetry_data.loc[c,"Speed"]) + " < " + str(d2_telemetry_data.loc[c,"Speed"]))
                            plt.scatter(d2_telemetry_data.loc[c,"X"],d2_telemetry_data.loc[c,"Y"],color=d2_color,s=2,label=d2_name)
                    except Exception as e:
                        print(e)
                        
                plt.title(f"{d1_name} vs {d2_name}\n{year} {str(race.event.EventName)}\nTrack Dominance on Fastest Lap",fontdict = {'fontsize' : 'small'})
                plt.grid(visible=False, which='both')
                # set up legend
                d1_patch = mpatches.Patch(color=d1_color, label=d1_name)
                d2_patch = mpatches.Patch(color=d2_color, label=d2_name)
                plt.legend(handles=[d1_patch, d2_patch])
                # save plot
                plt.rcParams['savefig.dpi'] = 300
                plt.savefig("cogs/plots/speed/"+race.date.strftime('%Y-%m-%d_%I%M')+f"_{sessiontype.name}_"+"_speed_"+d1_name+'vs'+d2_name+'.png')
                file = discord.File("cogs/plots/speed/"+race.date.strftime('%Y-%m-%d_%I%M')+f"_{sessiontype.name}_"+"_speed_"+d1_name+'vs'+d2_name+'.png', filename="image.png")
                message_embed.description = '' + str(race.date.year)+' '+str(race.event.EventName)+ '\n' + driver1+" vs "+driver2
                # reset plot just in case
                plt.clf()
                plt.cla()
                plt.close()
                return file
            except Exception as f:
                traceback.print_exc()
        # try to access the graph
        try:
            file = discord.File("cogs/plots/speed/"+race.date.strftime('%Y-%m-%d_%I%M')+f"_{sessiontype.name}_"+"_speed_"+d1_name+'vs'+d2_name+'.png', filename="image.png")
            message_embed.description = '' + str(race.date.year)+' '+str(race.event.EventName)+ '\n' + driver1+" vs "+driver2
            message_embed.set_footer(text='')
            print('found file')
            return file
        
        except Exception as e:
            # try to access the graph by switching driver1 and driver2 in filename
            try:
                file = discord.File("cogs/plots/speed/"+race.date.strftime('%Y-%m-%d_%I%M')+f"_{sessiontype.name}_"+"_speed_"+d2_name+'vs'+d1_name+'.png', filename="image.png")
                message_embed.description = '' + str(race.date.year)+' '+str(race.event.EventName)+ '\n' + driver1+" vs "+driver2
                message_embed.set_footer(text='')
                print("Swapped drivers around and found a file")
                return file
            # file does not exist and could not be created
            except:
                message_embed.set_footer(text="Likely an unsupported input (year/round) was given \n *(2018+)*")
                return
    # 
    except Exception as e:
        print(e)
        traceback.print_exc()
        message_embed.set_footer(text = e)
    
class Speed(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        print('Speed cog loaded')



    @app_commands.command(name='trackdominance', description='See track dominance between drivers on their personal fastest laps')
    
    # inputs
    @app_commands.describe(sessiontype='Choose between Race or Qualifying')
    @app_commands.choices(sessiontype=[
        app_commands.Choice(name="Qualifying", value="Q"),
        app_commands.Choice(name="Race", value="R"),
        ])
    @app_commands.describe(driver1='3 Letter Code for Driver 1')
    @app_commands.describe(driver2='3 Letter Code for Driver 2')
    @app_commands.describe(round='Round name or number (Australia or 3)')
    @app_commands.describe(year = "Year")
    
    # command
    async def speed(self, interaction: discord.Interaction, driver1: str, driver2: str, round:str, sessiontype: app_commands.Choice[str],year: typing.Optional[int]):
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
        file = await loop.run_in_executor(None, speed_results, driver1, driver2, round, year, sessiontype)
        # send embed
        try:
            message_embed.set_image(url='attachment://image.png')
            message_embed.set_footer(text="*Some lap data may be missing")
            await interaction.followup.send(embed=message_embed,file=file)
        except:
            message_embed.set_image(url='https://media.tenor.com/lxJgp-a8MrgAAAAd/laeppa-vika-half-life-alyx.gif')
            message_embed.description += "\nError Occured :("            
            await interaction.followup.send(embed=message_embed)
        loop.close()


async def setup(bot):
    await bot.add_cog(Speed(bot))

# speed_results(2023,1,"PER","VER",1)