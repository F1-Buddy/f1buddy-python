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
message_embed = discord.Embed(title="Fastest Lap Telemetry", description="")
message_embed.colour = colors.default
message_embed.set_author(name='f1buddy',icon_url='https://raw.githubusercontent.com/F1-Buddy/f1buddy-python/main/botPics/f1pythonpfp.png')
message_embed.set_thumbnail(
url='https://cdn.discordapp.com/attachments/884602392249770087/1059464532239581204/f1python128.png')

def td_to_laptime(td):
    td_microseconds = td.microseconds
    td_seconds = td.seconds
    td_minutes = td_seconds // 60
    td_seconds = str(td_seconds % 60).zfill(2)
    td_thousandths = str(td_microseconds)[:-3].ljust(3, '0')
    return f"{td_minutes}:{td_seconds}.{td_thousandths}"

def telemetry_results(driver1: str, driver2: str, round:str, year: typing.Optional[int], sessiontype):
    message_embed.description = ""
    message_embed.title = f"Fastest Lap {sessiontype.name.capitalize()} Telemetry"
    message_embed.set_footer(text="")
    # pyplot setup
    f1plt.setup_mpl()
    fig, ax = plt.subplots(3)
    ax[1].set_ylim([0, 105])
    ax[0].set_ylim([0, 360])
    ax[2].set_ylim([0,1.1])
    plt.subplots_adjust(left = 0.06, right = 0.99, top = 0.9, hspace=0.8)
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
        d1_fl = (race.laps.pick_driver(d1_number).pick_fastest()["LapTime"])
        d2_fl = (race.laps.pick_driver(d2_number).pick_fastest()["LapTime"])

        throttle_string = ""
        brake_string = ""

        if (not os.path.exists("cogs/plots/telemetry/"+race.date.strftime('%Y-%m-%d_%I%M')+"_telemetry_"+d1_name+'vs'+d2_name+'.png')) and (
            not os.path.exists("cogs/plots/telemetry/"+race.date.strftime('%Y-%m-%d_%I%M')+"_telemetry_"+d2_name+'vs'+d1_name+'.png')):
            try:
                d1_tel = d1_fastest.get_telemetry()
                d2_tel = d2_fastest.get_telemetry()
                # get driver color
                if (year == now.year):
                    d1_color = f1plt.driver_color(d1_name)
                    d2_color = f1plt.driver_color(d2_name)
                else:
                    d1_color = f"#{race.results.loc[str(d1_number),'TeamColor']}"
                    d2_color = f"#{race.results.loc[str(d2_number),'TeamColor']}"
                if d1_color == d2_color:
                    d2_color = 'white'
                    
                d1_patch = mpatches.Patch(color=d1_color, label=d1_name)
                d2_patch = mpatches.Patch(color=d2_color, label=d2_name)
                
                ax[0].yaxis.set_major_locator(MultipleLocator(100))

                ax[0].plot(d1_tel["Speed"],color=d1_color)
                ax[0].plot(d2_tel["Speed"],color=d2_color)
                ax[0].set_title("Speed")
                ax[1].plot(d1_tel["Throttle"],color=d1_color)
                ax[1].plot(d2_tel["Throttle"],color=d2_color)
                ax[1].set_title("Throttle")
                ax[2].plot(d1_tel["Brake"],color=d1_color)
                ax[2].plot(d2_tel["Brake"],color=d2_color)
                ax[2].set_title("Brake")

                total=len(d1_tel)
                ax[0].set_xlim([0,total])
                ax[1].set_xlim([0,total])
                ax[2].set_xlim([0,total])
                
                d1_throttle_percent = 0
                d2_throttle_percent = 0
                d1_brake_percent = 0
                d2_brake_percent = 0
                
                try:
                    for c in d1_tel.index:
                        if (d1_tel.loc[c,'Throttle'] >= 99):
                            d1_throttle_percent += 1
                        if (d1_tel.loc[c,'Brake'] == 1):
                            d1_brake_percent += 1
                        if (d2_tel.loc[c,'Throttle'] >= 99):
                            d2_throttle_percent += 1
                        if (d2_tel.loc[c,'Brake'] == 1):
                            d2_brake_percent += 1
                except Exception as e:
                    print(e)
                d1_throttle_percent = d1_throttle_percent / total * 100
                d2_throttle_percent = d2_throttle_percent / total * 100
                d1_brake_percent = d1_brake_percent / total * 100
                d2_brake_percent = d2_brake_percent / total * 100
                
                
                throttle_string += f"{d1_name} was on full throttle for {d1_throttle_percent:.2f}% of the lap\n"
                throttle_string += f"{d2_name} was on full throttle for {d2_throttle_percent:.2f}% of the lap\n"
                brake_string += f"{d1_name} was on full throttle for {d1_brake_percent:.2f}% of the lap\n"
                brake_string += f"{d2_name} was on full throttle for {d2_brake_percent:.2f}% of the lap\n"
                print(throttle_string)
                print(brake_string)
                        
                # plt.title(f"Lap Telemetry\n{year} {str(race.event.EventName)}\n{d1_name} vs {d2_name}",fontdict = {'fontsize' : 'small'})
                plt.grid(visible=False, which='both')
                # set up legend
                d1_patch = mpatches.Patch(color=d1_color, label=d1_name)
                d2_patch = mpatches.Patch(color=d2_color, label=d2_name)
                plt.legend(handles=[d1_patch, d2_patch],bbox_to_anchor=(1.01, 5.2),loc='upper right')
                # save plot
                plt.rcParams['savefig.dpi'] = 300
                plt.savefig("cogs/plots/telemetry/"+race.date.strftime('%Y-%m-%d_%I%M')+"_telemetry_"+d1_name+'vs'+d2_name+'.png')
                file = discord.File("cogs/plots/telemetry/"+race.date.strftime('%Y-%m-%d_%I%M')+"_telemetry_"+d1_name+'vs'+d2_name+'.png', filename="image.png")
                # message_embed.description = '' + str(race.date.year)+' '+str(race.event.EventName)+ " "+sessiontype.name.capitalize()+ '\n' + driver1+" vs "+driver2
                message_embed.description = f"{race.date.year} {race.event.EventName} {sessiontype.name.capitalize()}\n{driver1}: {td_to_laptime(d1_fl)}\n{driver2}: {td_to_laptime(d2_fl)}\nΔ = ±{td_to_laptime(abs(d1_fl-d2_fl))}"
                # message_embed.description += "\n" + throttle_string + brake_string
                # reset plot just in case
                plt.clf()
                plt.cla()
                plt.close()
                return file
            except Exception as f:
                traceback.print_exc()
        # try to access the graph
        try:
            print("already exists")
            file = discord.File("cogs/plots/telemetry/"+race.date.strftime('%Y-%m-%d_%I%M')+"_telemetry_"+d1_name+'vs'+d2_name+'.png', filename="image.png")
            # message_embed.description = '' + str(race.date.year)+' '+str(race.event.EventName)+ " "+sessiontype.name.capitalize()+ '\n' + driver1+" vs "+driver2
            message_embed.description = f"{race.date.year} {race.event.EventName} {sessiontype.name.capitalize()}\n{driver1}: {td_to_laptime(d1_fl)}\n{driver2}: {td_to_laptime(d2_fl)}\nΔ = ±{td_to_laptime(abs(d1_fl-d2_fl))}"
            message_embed.set_footer(text='')
            print('found file')
            return file
        
        except Exception as e:
            print(e)
            # try to access the graph by switching driver1 and driver2 in filename
            try:
                file = discord.File("cogs/plots/telemetry/"+race.date.strftime('%Y-%m-%d_%I%M')+"_telemetry_"+d2_name+'vs'+d1_name+'.png', filename="image.png")
                # message_embed.description = '' + str(race.date.year)+' '+str(race.event.EventName)+ " "+sessiontype.name.capitalize()+ '\n' + driver1+" vs "+driver2
                message_embed.description = f"{race.date.year} {race.event.EventName} {sessiontype.name.capitalize()}\n{driver1}: {td_to_laptime(d1_fl)}\n{driver2}: {td_to_laptime(d2_fl)}\nΔ = ±{td_to_laptime(abs(d1_fl-d2_fl))}"
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
    
class Telemetry(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        print('Telemetry cog loaded')

    @app_commands.command(name='telemetry', description='See telemetry between 2 drivers on their fastest laps in a race')
    @app_commands.describe(sessiontype='Choose between Race or Qualifying')
    @app_commands.choices(sessiontype=[
        app_commands.Choice(name="Qualifying", value="Q"),
        app_commands.Choice(name="Race", value="R"),
        ])
    # inputs
    @app_commands.describe(driver1='3 Letter Code for Driver 1')
    @app_commands.describe(driver2='3 Letter Code for Driver 2')
    @app_commands.describe(round='Round name or number (Australia or 3)')
    @app_commands.describe(year = "Year")
    
    # command
    async def telemetry(self, interaction: discord.Interaction, driver1: str, driver2: str, round:str, sessiontype: app_commands.Choice[str], year: typing.Optional[int]):
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
        file = await loop.run_in_executor(None, telemetry_results, driver1, driver2, round, year, sessiontype)
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
    await bot.add_cog(Telemetry(bot))

# telemetry_results(2023,1,"PER","VER",1)