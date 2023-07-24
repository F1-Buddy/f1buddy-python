import asyncio
import os
import discord
import fastf1
from matplotlib.ticker import MultipleLocator
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.offsetbox import OffsetImage, AnnotationBbox
from matplotlib import cbook, image, pyplot as plt
import pandas as pd
from discord import app_commands
from discord.ext import commands
from lib.colors import colors
from lib.drivernames import driver_names
from lib.teamcolors import team_colors
from datetime import datetime
from lib.f1font import regular_font, bold_font
current_year = datetime.now().year
now = pd.Timestamp.now()
fastf1.Cache.enable_cache('cache/')
message_embed = discord.Embed(title=f"Average Positions", description="Average Positions") # boilerplate/initalization for global scope

def plot_avg_positions(event):
    sessiontype = str(event.name) # convert discord choice to string
    
    # get latest completed session by starting from the end of calendar and going back towards the beginning of the season, use this to check for race date in png's
    year_sched = fastf1.get_event_schedule(current_year,include_testing=False)
    round_check = (year_sched.shape[0])
    if (year_sched.loc[round_check, "EventFormat"] == 'conventional'):
        sessionTime = year_sched.loc[round_check,"Session4Date"].tz_convert('America/New_York')
    else:
        sessionTime = year_sched.loc[round_check,"Session2Date"].tz_convert('America/New_York')
    while (now.tz_localize('America/New_York') < sessionTime):
        round_check -= 1
        if (year_sched.loc[round_check, "EventFormat"] == 'conventional'):
            sessionTime = year_sched.loc[round_check,"Session4Date"].tz_convert('America/New_York')
        else:
            sessionTime = year_sched.loc[round_check,"Session2Date"].tz_convert('America/New_York') 
    race = fastf1.get_session(current_year, round_check, f"{sessiontype}") 
    
    filename = f"cogs/plots/avgpos/avgpos_{race.date.strftime('%Y-%m-%d_%I%M')}_{sessiontype}.png"
    if not os.path.exists(filename): # checks if image has already been generated
        # calculate average positions
        driver_positions, driver_teams, driver_colors = avg_pos(sessiontype)
        driver_codes = [driver_names.get(name) for name in driver_positions.keys()] # converts to three-letter driver code
        avg_positions = [round(sum(positions) / len(positions), 2) for positions in driver_positions.values()]
        
        driver_codes, avg_positions, driver_teams = zip(*sorted(zip(driver_codes, avg_positions, driver_teams), key=lambda x: x[1])) # sort drivers based on average positions
        print(driver_codes)
        race.load(laps=True,telemetry=False,weather=False,messages=False)
        resultsTable = race.results
        print(resultsTable)
        colors_for_drivers = ['#' + driver_colors.get(code, 'gray') for code in driver_codes]
        print(colors_for_drivers)
            
        watermark_img = plt.imread('botPics/f1pythonpfp.png')
        fig, ax = plt.subplots(figsize=(16.8, 10.5)) # create the bar plot and size

        ax.barh(range(len(driver_codes)), avg_positions, color=colors_for_drivers)
            
        # setting x-axis label, title
        ax.set_xlabel("Position", fontproperties=regular_font, fontsize=20, labelpad=20)
        ax.set_title(f"Average {sessiontype} Finish Position {current_year}", fontproperties=bold_font, fontsize=20, pad=20)

        # space between limits for the y-axis and x-axis
        print(len(driver_codes))
        ax.set_ylim(-0.8, len(driver_codes)-0.25)
        ax.set_xlim(0, 20.1)
        ax.invert_yaxis() # invert y axis, top to bottom
        ax.xaxis.set_major_locator(MultipleLocator(1)) # amount x-axis increments by 1

        # remove ticks, keep labels
        ax.xaxis.set_tick_params(labelsize=12)
        ax.yaxis.set_tick_params(labelsize=12)
        ax.set_xticklabels(ax.get_xticklabels(), fontproperties=regular_font, fontsize=20)
        ax.set_yticklabels(driver_codes, fontproperties=bold_font, fontsize=20)
        ax.set_yticks(range(len(driver_codes)))
        ax.tick_params(axis='both', length=0, pad=8)
        # ax.tick_params(axis='y', length=0)

        # remove all lines, bar the x-axis grid lines
        ax.yaxis.grid(False)
        ax.spines['top'].set_visible(False)
        ax.spines['bottom'].set_visible(False)
        ax.spines['left'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.minorticks_off()
        
        # set blackground
        ax.set_facecolor('black')    
        fig.set_facecolor('black')
        # Step 3: Overlay the image at the bottom left corner of the chart
        # Adjust the position (x and y) to place the watermark as desired
        try:
            watermark_box = OffsetImage(watermark_img, zoom=0.2)  # Adjust the zoom factor as needed
            ab = AnnotationBbox(watermark_box, (0,1), xycoords='axes fraction', frameon=False)
            ax.add_artist(ab)

            # Step 4: Add text on top of the image to further customize the watermark
            # Replace 'Your Watermark Text' with your desired text
            ax.text(0.02, 0.02, 'Your Watermark Text', transform=ax.transAxes,
                    fontsize=12, color='gray', alpha=0.7)
        except Exception as e:
            print(e)
        # np.random.seed(19680801)
        # ax.plot(np.random.rand(20), '-o', ms=20, lw=2, alpha=0.7, mfc='orange')
        # ax.grid()

        # ax.text(0.5, 0.5, 'created with matplotlib', transform=ax.transAxes,
        #         fontsize=40, color='gray', alpha=0.5,
        #         ha='center', va='center', rotation=30)

        # adds position number near bars
        for i, (code, position, team) in enumerate(zip(driver_codes, avg_positions, driver_teams)):
            ax.text(position + 0.1, i, f"   {str(position)}", va='center', fontproperties=regular_font, fontsize=20)
            
        plt.savefig(f"cogs/plots/avgpos/avgpos_{race.date.strftime('%Y-%m-%d_%I%M')}_{sessiontype}.png") # save plot
        
    try:
        file = discord.File(f"cogs/plots/avgpos/avgpos_{race.date.strftime('%Y-%m-%d_%I%M')}_{sessiontype}.png", filename="image.png")
        return file
    except Exception as e:
        print(e)
        message_embed.set_footer(text=e)
        
def avg_pos(sessiontype):
    # get latest completed session by starting from the end of calendar and going back towards the beginning of the season
    year_sched = fastf1.get_event_schedule(current_year, include_testing=False)
    num_rounds = year_sched.shape[0]
    driver_positions, driver_teams, driver_colors = {}, [], {} # driver_pos keeps driver name and pos, driver_teams keeps order of driver positions by teamname

    for round_num in range(1, num_rounds + 1):
        sessionTime = year_sched.loc[round_num, "Session4Date"].tz_convert('America/New_York') if year_sched.loc[round_num, "EventFormat"] == 'conventional' else year_sched.loc[round_num, "Session2Date"].tz_convert('America/New_York')
        if now.tz_localize('America/New_York') < sessionTime:
            break
        
        try:
            result_session = fastf1.get_session(current_year, round_num, sessiontype)
            result_session.load(laps=True,telemetry=False,weather=False,messages=False)
            resultsTable = result_session.results
            print("A")
        except Exception as e:
            print(f"An error occurred in round {round_num}: {e}")
            continue

        print("b")
        try:
            print("C")
            for index, row in resultsTable.iterrows():
                driver_code = row['Abbreviation']
                team_color = row['TeamColor']
                
                driver_colors[driver_code] = team_color
        except Exception as e:
            print(e)

        for i in resultsTable.DriverNumber.values:
            try:
                team_name = resultsTable.loc[i, 'TeamName']
            except:
                pass
            driver_positions.setdefault(resultsTable.loc[i, 'FullName'], []).append(int(resultsTable.loc[i, 'Position']))
            driver_teams.append(team_name)  # add team name to the separate list
            
    return driver_positions, driver_teams, driver_colors # driver_positions returns positions of drivers through races, driver_teams is the corresponding team names for each driver

def head_to_head_results():
    driver_positions = avg_pos()
    head_to_head = {}

    for driver1 in driver_positions:
        for driver2 in driver_positions:
            if driver1 != driver2:
                driver1_positions = driver_positions[driver1]
                driver2_positions = driver_positions[driver2]

                # Calculate the number of times each driver finished ahead of the other
                driver1_wins = sum(pos1 < pos2 for pos1, pos2 in zip(driver1_positions, driver2_positions))
                driver2_wins = sum(pos1 > pos2 for pos1, pos2 in zip(driver1_positions, driver2_positions))

                head_to_head_key = f"{driver1} vs {driver2}"
                head_to_head[head_to_head_key] = f"{driver1_wins}-{driver2_wins}"

    return head_to_head

class AveragePos(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        
    @commands.Cog.listener()
    async def on_ready(self):
        print('Avg Positions cog loaded')
        
    @app_commands.command(name='avgpos', description='See average finish position for driver for race/qualifying throughout the year')
    @app_commands.describe(event='Choose between Qualifying or Race')
    @app_commands.choices(event=[app_commands.Choice(name="Qualifying", value="Qualifying"), app_commands.Choice(name="Race", value="Race"),])
    async def positions(self, interaction: discord.Interaction, event: app_commands.Choice[str]):
        message_embed = discord.Embed(title=f"Average {event.name} Finish Position {current_year}", description="")
        message_embed.colour = colors.default
        message_embed.set_author(name='f1buddy',icon_url='https://raw.githubusercontent.com/F1-Buddy/f1buddy-python/main/botPics/f1pythonpfp.png')
        message_embed.set_thumbnail(
        url='https://cdn.discordapp.com/attachments/884602392249770087/1059464532239581204/f1python128.png')
        await interaction.response.defer()
        loop = asyncio.get_running_loop()
        file = await loop.run_in_executor(None, plot_avg_positions, event)
        try:
            message_embed.set_image(url='attachment://image.png')
            await interaction.followup.send(embed=message_embed,file=file)
        except Exception as e:
            message_embed.set_image(url='https://media.tenor.com/lxJgp-a8MrgAAAAd/laeppa-vika-half-life-alyx.gif')
            message_embed.description = f"Error Occured :( {e}"            
            await interaction.followup.send(embed=message_embed)
        loop.close()

async def setup(bot):
    await bot.add_cog(AveragePos(bot))