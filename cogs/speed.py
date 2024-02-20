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
from lib.f1font import regular_font, bold_font
import matplotlib.patches as mpatches
from matplotlib.collections import LineCollection
from matplotlib.colors import ListedColormap
from lib.colors import colors
import pandas as pd
import fastf1.plotting as f1plt
import numpy as np
import repeated.common as cm

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
    if sessiontype.name.startswith("FP"):
        message_embed.title = f"Track Dominance During {sessiontype.name}"
    else:
        message_embed.title = f"Track Dominance During {sessiontype.name.capitalize()}"
    message_embed.set_footer(text="")
    # pyplot setup
    f1plt.setup_mpl()
    fig, ax = plt.subplots(figsize=(7.5,6))
    fig.set_facecolor('black')
    ax.set_facecolor('black')
    ax.axis('equal')
    ax.axis('off')
    try:
        # no year given
        if (year is None) or (year > now.year) or (year < 2018):
            event_year = now.year
            if (cm.currently_offseason()[0]) or (cm.latest_completed_index(now.year) == 0):
                event_year = event_year - 1
        else:
            event_year = year
        # get proper round (string/int)
        try:
            # given as int
            event_round = int(round)
        except ValueError:
            # given as string
            event_round = round

        # get session using given args
        race = fastf1.get_session(event_year, event_round, sessiontype.value)

        race.load(laps=True,telemetry=True,weather=False,messages=False)
        message_embed.description = race.event.EventName
        # get driver data for their fastest lap during the session
        d1_laps = race.laps.pick_driver(driver1)
        d1_fastest = d1_laps.pick_fastest()
        d1_number = d1_laps.iloc[0].loc['DriverNumber']
        d1_name = driver1
        
        d2_laps = race.laps.pick_driver(driver2)
        d2_fastest = d2_laps.pick_fastest()
        d2_number = d2_laps.iloc[0].loc['DriverNumber']
        d2_name = driver2
        
        # check if graph already exists, if not create it
        if (not os.path.exists("cogs/plots/speed/"+race.date.strftime('%Y-%m-%d_%I%M')+f"_{sessiontype.name}_"+"_speed_"+d1_name+'vs'+d2_name+'.png')) and (
            not os.path.exists("cogs/plots/speed/"+race.date.strftime('%Y-%m-%d_%I%M')+f"_{sessiontype.name}_"+"_speed_"+d2_name+'vs'+d1_name+'.png')):
            try:
                # get driver telemetry
                d1_telemetry_data = d1_fastest.get_telemetry()
                d2_telemetry_data = d2_fastest.get_telemetry()
                
                # get driver color
                if (year == now.year):
                    # fastf1.plotting.driver_color() only supports current season
                    d1_color = f1plt.driver_color(d1_name)
                    d2_color = f1plt.driver_color(d2_name)
                else:
                    # otherwise use team color
                    d1_color = f"#{race.results.loc[str(d1_number),'TeamColor']}"
                    d2_color = f"#{race.results.loc[str(d2_number),'TeamColor']}"
                if d1_color == d2_color:
                    # if comparing teammates, make second driver white (unless first driver is already white Ex: Haas)
                    if (d1_color == '#ffffff'):
                        d2_color = 'grey'
                    else:
                        d2_color = 'white'
                
                # We want 25 mini-sectors
                num_minisectors = 25

                # What is the total distance of a lap?
                total_distance = max(d1_telemetry_data['Distance'])

                # Generate equally sized mini-sectors 
                minisector_length = total_distance / num_minisectors

                minisectors = [0]

                for i in range(0, (num_minisectors - 1)):
                    minisectors.append(minisector_length * (i + 1))
                    
                # add columns for minisector number and minisector average speed
                d1_telemetry_data['Minisector'] =  d1_telemetry_data['Distance'].apply(
                    lambda z: (
                        minisectors.index(
                        min(minisectors, key=lambda x: abs(x-z)))+1
                    )
                )
                avg_speeds1 = d1_telemetry_data.groupby("Minisector")["Speed"].mean()
                d1_telemetry_data["Minisector_Speed"] = d1_telemetry_data["Minisector"].map(avg_speeds1)
                
                d2_telemetry_data['Minisector'] =  d2_telemetry_data['Distance'].apply(
                    lambda z: (
                        minisectors.index(
                        min(minisectors, key=lambda x: abs(x-z)))+1
                    )
                )
                avg_speeds2 = d2_telemetry_data.groupby("Minisector")["Speed"].mean()
                d2_telemetry_data["Minisector_Speed"] = d2_telemetry_data["Minisector"].map(avg_speeds2)
                
                # add another column for driver color
                d1_telemetry_data['Driver_Color'] = d1_color
                d2_telemetry_data['Driver_Color'] = d2_color
                
                # get the greatest average speed per minisector
                d1_avg_speeds = d1_telemetry_data.groupby("Minisector")["Minisector_Speed"].max()
                d2_avg_speeds = d2_telemetry_data.groupby("Minisector")["Minisector_Speed"].max()
                max_avg_speeds = []
                for i in d1_avg_speeds.index:
                    if (d1_avg_speeds[i] >= d2_avg_speeds[i]):
                        max_avg_speeds.append(d1_avg_speeds[i])
                    else:
                        max_avg_speeds.append(d2_avg_speeds[i])
                # Create a new dataframe combining the "X", "Y", "Minisector", and "Minisector_Speed" columns from both dataframes
                combined_data = pd.concat([d1_telemetry_data[['X', 'Y', 'Minisector', 'Minisector_Speed','Driver_Color']], d2_telemetry_data[['X', 'Y', 'Minisector', 'Minisector_Speed','Driver_Color']]])
                df_list = []
                for i in range(25):
                    df_list.append(combined_data.loc[combined_data['Minisector_Speed'] == max_avg_speeds[i]])
                filtered_df = pd.concat(df_list)
                # remove duplicate rows
                filtered_df = filtered_df.loc[filtered_df.groupby(filtered_df.index)['Minisector_Speed'].idxmax()]
                
                # create color array for each segment of line
                color_array = []
                
                # compare speed in each sector and add faster driver's color to color_array
                x = filtered_df["X"].to_list()
                y = filtered_df["Y"].to_list()
                x = d1_telemetry_data["X"].to_list()
                y = d1_telemetry_data["Y"].to_list()
                for i in filtered_df.index:
                    try:
                        row_color = filtered_df.loc[i,"Driver_Color"]
                        # use faster driver's color
                        if (type(row_color)) == str:
                            if (row_color == d1_color):
                                color_array.append(1)
                            elif (row_color == d2_color):
                                color_array.append(2)
                    # when there is no data for either driver for a sector, make the color black
                    except Exception as e:
                        # traceback.print_exc()
                        color_array.append(None)
                        print(i)

                # some numpy fuckery to turn x and y lists to coords idk how this works
                points = np.array([x, y]).T.reshape(-1, 1, 2)
                segments = np.concatenate([points[:-1], points[1:]], axis=1)
                
                # colormap
                cmap = ListedColormap([d1_color,d2_color])
                # setup LineCollection
                lc = LineCollection(segments,cmap=cmap)
                lc.set_array(color_array)
                lc.set_linewidth(2)
                # plot line
                plt.gca().add_collection(lc)
                plt.gca().axis('equal')
                # more plot setup
                plt.title(f"{d1_name} vs {d2_name}\n{str(race.date.year)} {str(race.event.EventName)} {sessiontype.name.capitalize()}\nTrack Dominance on Fastest Lap",fontproperties=bold_font)
                plt.grid(visible=False, which='both')
                # set up legend
                d1_patch = mpatches.Patch(color=d1_color, label=d1_name)
                d2_patch = mpatches.Patch(color=d2_color, label=d2_name)
                plt.legend(handles=[d1_patch, d2_patch], prop=bold_font)
                # save plot
                plt.rcParams['savefig.dpi'] = 300
                watermark_img = plt.imread('botPics/f1pythoncircular.png') # set directory for later use
                try:
                    # add f1buddy pfp
                    watermark_box = OffsetImage(watermark_img, zoom=0.2) 
                    ab = AnnotationBbox(watermark_box, (-0.075,-0.05), xycoords='axes fraction', frameon=False)
                    ax.add_artist(ab)

                    # add text next to it
                    ax.text(0.025,-0.075, 'Made by F1Buddy Discord Bot', transform=ax.transAxes,
                            fontsize=12,fontproperties=bold_font)
                except Exception as e:
                    print(e)
                # plt.show()
                # plt.show()
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
        app_commands.Choice(name="FP1", value="FP1"),
        app_commands.Choice(name="FP2", value="FP2"),
        app_commands.Choice(name="FP3", value="FP3"),
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
            message_embed.set_footer(text="")
            await interaction.followup.send(embed=message_embed,file=file)
        except:
            message_embed.set_image(url='https://media.tenor.com/lxJgp-a8MrgAAAAd/laeppa-vika-half-life-alyx.gif')
            message_embed.description += "\nError Occured :("            
            await interaction.followup.send(embed=message_embed)
        loop.close()


async def setup(bot):
    await bot.add_cog(Speed(bot))

# speed_results(2023,1,"PER","VER",1)