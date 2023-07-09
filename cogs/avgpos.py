import asyncio
import discord
import fastf1
from matplotlib.ticker import MultipleLocator
import pandas as pd
from matplotlib import font_manager, pyplot as plt
import pandas as pd
from discord import app_commands
from discord.ext import commands
from lib.colors import colors
from lib.drivernames import driver_names
from lib.teamcolors import team_colors
from datetime import datetime
current_year = datetime.now().year
now = pd.Timestamp.now()
fastf1.Cache.enable_cache('cache/')
message_embed = discord.Embed(title=f"Average Positions", description="Average Positions") # boilerplate/initalization for global scope

def plot_avg_positions(event):
    # convert discord choice to string
    sessiontype = str(event.name)
    
    # set fonts
    regular_font_path = "fonts/Formula1-Regular.ttf"
    bold_font_path = "fonts/Formula1-Bold.ttf"
    regular_font = font_manager.FontProperties(fname=regular_font_path)
    bold_font = font_manager.FontProperties(fname=bold_font_path)
    
    # calculate average positions
    driver_positions, driver_teams = avg_pos(sessiontype)
    driver_codes = [driver_names.get(name) for name in driver_positions.keys()] # converts to three-letter driver code
    avg_positions = [round(sum(positions) / len(positions), 2) for positions in driver_positions.values()]

    # sort drivers based on average positions
    driver_codes, avg_positions, driver_teams = zip(*sorted(zip(driver_codes, avg_positions, driver_teams), key=lambda x: x[1]))

    fig, ax = plt.subplots(figsize=(7.5, 5)) # create the bar plot and size
    ax.barh(range(len(driver_codes)), avg_positions, color=[team_colors.get(team, 'gray') for team in driver_teams]) # plotting the horizontal bar chart

    # setting x-axis label, title
    ax.set_xlabel("Position", fontproperties=regular_font, labelpad=10)
    ax.set_title(f"Average {sessiontype} Position {current_year}", fontproperties=bold_font)

    # space between limits for the y-axis and x-axis
    ax.set_ylim(-0.8, 19.8)
    ax.set_xlim(0, 20.1)
    ax.invert_yaxis() # invert y axis, top to bottom
    ax.xaxis.set_major_locator(MultipleLocator(1)) # amount x-axis increments by 1

    # remove ticks, keep labels
    ax.xaxis.set_tick_params(labelsize=12)
    ax.yaxis.set_tick_params(labelsize=12)
    ax.set_xticklabels(ax.get_xticklabels(), fontproperties=regular_font)
    ax.set_yticks(range(len(driver_codes)))
    ax.set_yticklabels(driver_codes, fontproperties=bold_font)
    ax.tick_params(axis='x', length=0)
    ax.tick_params(axis='y', length=0)

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

    # adds position number near bars
    for i, (code, position, team) in enumerate(zip(driver_codes, avg_positions, driver_teams)):
        ax.text(position + 0.1, i, f"   {str(position)}", va='center', fontproperties=regular_font)

    plt.savefig("cogs/plots/avgpos/avg_pos.png") # save plot
    
    try:
        file = discord.File("cogs/plots/avgpos/avg_pos.png", filename="image.png")
        return file
    except Exception as e:
        print(e)
        message_embed.set_footer(text=e)
        
def avg_pos(sessiontype):
    # get latest completed session by starting from the end of calendar and going back towards the beginning of the season
    year_sched = fastf1.get_event_schedule(current_year, include_testing=False)
    num_rounds = year_sched.shape[0]
    
    
    driver_positions, driver_teams = {}, [] # driver_pos keeps driver name and pos, driver_teams keeps order of driver positions by teamname
    total_positions, num_races = 0, 0
    
    for round_num in range(1, num_rounds + 1):
        sessionTime = year_sched.loc[round_num, "Session4Date"].tz_convert('America/New_York') if year_sched.loc[round_num, "EventFormat"] == 'conventional' else year_sched.loc[round_num, "Session2Date"].tz_convert('America/New_York')

        if now.tz_localize('America/New_York') < sessionTime:
            break
        
        try:
            result_session = fastf1.get_session(current_year, round_num, sessiontype)
            result_session.load()
            resultsTable = result_session.results
        except Exception as e:
            print(f"An error occurred in round {round_num}: {e}")
            continue
        
        driver_names = ""
        position_string = "" 

        for i in resultsTable.DriverNumber.values:
            try:
                team_name = resultsTable.loc[i, 'TeamName']
                driver_names += resultsTable.loc[i, 'FullName'] + "\n"
            except:
                driver_names += resultsTable.loc[i, 'FullName'] + "\n"
            try:
                temp = str(resultsTable.loc[i, 'Position'])
                position_string += temp[0:temp.index('.')] + "\n"
            except ValueError:
                print(f"No time set for driver {resultsTable.loc[i, 'FullName']} in round {round_num}")
                continue
            except KeyError:
                print(f"Driver {resultsTable.loc[i, 'FullName']} did not appear in round {round_num}")
                continue
            except Exception as e:
                print(f"An error occurred for driver {resultsTable.loc[i, 'FullName']} in round {round_num}: {e}")
                message_embed.set_image(url='https://media.tenor.com/lxJgp-a8MrgAAAAd/laeppa-vika-half-life-alyx.gif')
                message_embed.description = "Error Occured :( \n {e}"            
                continue
            
            driver_positions.setdefault(resultsTable.loc[i, 'FullName'], []).append(int(resultsTable.loc[i, 'Position']))
            driver_teams.append(team_name)  # add team name to the separate list
    # for driver, positions in driver_positions.items(): # test values with string
    #     avg_position = round(sum(int(pos) for pos in positions) / len(positions), 2)
    #     print(f"{driver} Average {sessiontype} Position {avg_position}")
    #     total_positions += sum(positions)
    #     num_races += len(positions)
    return driver_positions, driver_teams

class AveragePos(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        
    @commands.Cog.listener()
    async def on_ready(self):
        print('Avg Positions cog loaded')
        
    @app_commands.command(name='avgpos', description='See average position for driver for race/qualifying throughout the year. Will take some time to load.')
    @app_commands.describe(event='Choose between Qualifying or Race')
    @app_commands.choices(event=[app_commands.Choice(name="Qualifying", value="Qualifying"), app_commands.Choice(name="Race", value="Race"),])
    async def positions(self, interaction: discord.Interaction, event: app_commands.Choice[str]):
        message_embed = discord.Embed(title=f"Average {event.name} Position {current_year}", description=f"Average {event.name.lower()} positions throughout {current_year}")
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
        except:
            message_embed.set_image(url='https://media.tenor.com/lxJgp-a8MrgAAAAd/laeppa-vika-half-life-alyx.gif')
            message_embed.description = "Error Occured :("            
            await interaction.followup.send(embed=message_embed)
        loop.close()

async def setup(bot):
    await bot.add_cog(AveragePos(bot))