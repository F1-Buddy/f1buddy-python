import discord
import asyncio
import fastf1
import os
import traceback
import typing
from discord import app_commands
from discord.ext import commands
from matplotlib import pyplot as plt
from lib.f1font import regular_font, bold_font
import matplotlib.patches as mpatches
import matplotlib
from matplotlib.ticker import (MultipleLocator)
# matplotlib.use('agg')
from lib.colors import colors
import pandas as pd
import fastf1.plotting as f1plt
from matplotlib.offsetbox import OffsetImage, AnnotationBbox
# get current time
now = pd.Timestamp.now()
fastf1.Cache.enable_cache('cache/')
message_embed = discord.Embed(title=f"Average Gap between Teams", description="") # boilerplate/initalization for global scope

def addlabels(x,y,df):
    for i in range(len(x)):
        string = f"{str(y[i])[0:5].ljust(5,'0')}"
        plt.text(df.loc[i,'AveragePos']+1.5, i, string, va = 'center', fontproperties=bold_font)

def plot_avg_positions(year):
    try:
        if (year == None):
            year = now.year
        elif (year > now.year):
            year = now.year
            
        teams = []
        colors = []
        positions=[0,0,0,0,0,0,0,0,0,0]
        count = [0,0,0,0,0,0,0,0,0,0]
        latest_race_completed = None

        # get latest completed session by starting from the end of calendar and going back towards beginning of season
        year_sched = fastf1.get_event_schedule(year,include_testing=False)
        round = (year_sched.shape[0])
        sessionTime = year_sched.loc[round,"Session5Date"].tz_convert('America/New_York')
        # print(sessionTime)
        while (now.tz_localize('America/New_York') < sessionTime):
            round -= 1
            sessionTime = year_sched.loc[round,"Session5Date"].tz_convert('America/New_York')
        latest_race_completed = fastf1.get_session(year, round, 'Race')
        # most recent session found, load it
        print(round)
        latest_race_completed.load(laps=False, telemetry=False, weather=False, messages=False)
        latest_racedate = str(latest_race_completed.date)[:-9]
        lResults = latest_race_completed.results
        
        
        if (not os.path.exists("cogs/plots/avggapteam/"+latest_racedate+f"_AvgGapTeamFor{year}"+'.png')):
            # get team names
            for i in lResults['TeamName']:
                if i not in teams and i != 'nan':
                    teams.append(i)
                    # get teamcolor where teamname of row == i, get first value of those 2 using 0th index of the df
                    colors.append(f"#{lResults.loc[lResults['TeamName'] == i,'TeamColor'][lResults.loc[lResults['TeamName'] == i,'TeamColor'].index[0]]}") # this is pretty shit i just didnt feel like getting the first value in a better way
            
            # create df
            df = pd.DataFrame(teams, columns=['TeamName'])
            df = df.assign(TotalPositions=positions)
            df = df.assign(Count = count)
            df = df.assign(TeamColor = colors)
            average_position = []

            # print(lResults)
            while (round > 0):
                try:
                    latest_race_completed = fastf1.get_session(year, round, 'Race')
                    latest_race_completed.load(laps=False, telemetry=False, weather=False, messages=False)
                    lResults = latest_race_completed.results
                    # get positions (excluding dnfs)
                    for index, row in lResults.iterrows():
                        df.loc[df['TeamName'] == row['TeamName'],'TotalPositions'] += int(row['ClassifiedPosition'])
                        df.loc[df['TeamName'] == row['TeamName'],'Count'] += 1
                    
                except ValueError as e:
                    print(e)
                round -= 1
                    
            # calculate avg positions
            # do at the end
            for index, row in df.iterrows():
                average_position.append(row['TotalPositions']/row['Count'])
            df = df.assign(AveragePos = average_position)
            df = df.sort_values(by=['AveragePos'])
            df = df.reset_index(drop=True)
            print(df)

            # graphing
            f1plt._enable_fastf1_color_scheme()
            f1plt.setup_mpl(misc_mpl_mods=False)
            fig, ax = plt.subplots(figsize=(18, 12))
            fig.set_facecolor('black')
            ax.set_facecolor('black')

            plt.title(f"Average Gap Between Teams",fontproperties=bold_font, pad=20)
            plt.barh(df['TeamName'], df['AveragePos'],.9,color = df['TeamColor'])
            # plt.xlim(left=min(df['AveragePos'])-.5)
            plt.xlim(right=20)
            plt.xlabel("Average Finishing Position",fontproperties=regular_font)
            plt.ylim([9.5,-0.5])
            plt.subplots_adjust(left=0.17)
            for label in ax.get_xticklabels():
                label.set_fontproperties(bold_font)
            for label in ax.get_yticklabels():
                label.set_fontproperties(regular_font)

            for index, row in df.iterrows():
                teamname = row["TeamName"]
                try:
                    # use car images
                    car_img = plt.imread(f'lib/cars/{teamname}.png')
                    # use team logos
                    # car_img = plt.imread(f'lib/cars/logos/{teamname}.webp')
                    watermark_box = OffsetImage(car_img, zoom=0.2) 
                    ab = AnnotationBbox(watermark_box, ((row['AveragePos'])/(max(ax.get_xlim())),(0.95-.1*index)), xycoords='axes fraction', frameon=False)
                    ax.add_artist(ab)
                except:
                    try:
                        teamname = row["TeamName"][:-7]
                        # use car images
                        car_img = plt.imread(f'lib/cars/{teamname}.png')
                        # use team logos
                        # car_img = plt.imread(f'lib/cars/logos/{teamname}.webp')
                        watermark_box = OffsetImage(car_img, zoom=0.2) 
                        ab = AnnotationBbox(watermark_box, ((row['AveragePos'])/(max(ax.get_xlim())),(0.95-.1*index)), xycoords='axes fraction', frameon=False)
                        ax.add_artist(ab)
                    except:
                        print(f'Team {teamname} not supported')
                

            addlabels(df['TeamName'], df['AveragePos'],df)
            plt.rcParams['savefig.dpi'] = 300
            plt.savefig("cogs/plots/avggapteam/"+latest_racedate+f"_AvgGapTeamFor{year}"+'.png')
            # try to access the graph
        try:
            file = discord.File("cogs/plots/avggapteam/"+latest_racedate+f"_AvgGapTeamFor{year}"+'.png', filename="image.png")
            message_embed.set_footer(text="")
            return file
        
        except Exception as e:
            traceback.print_exc()
            message_embed.set_footer(text=e)
        # 
    except Exception as e:
        traceback.print_exc()
        message_embed.set_footer(text = e)
        

class AverageGapTeam(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        
    @commands.Cog.listener()
    async def on_ready(self):
        print('Avg Teams Gap cog loaded')
        
    @app_commands.command(name='avggaps', description='See the average performance gap between teams')
    # @app_commands.describe(event='Choose between Qualifying or Race')
    # @app_commands.choices(event=[app_commands.Choice(name="Qualifying", value="Qualifying"), app_commands.Choice(name="Race", value="Race"),])
    async def avggaps(self, interaction: discord.Interaction, year: typing.Optional[int]):
        message_embed = discord.Embed(title=f"Average Finishing Gap between Teams", description="")
        message_embed.colour = colors.default
        message_embed.set_author(name='f1buddy',icon_url='https://raw.githubusercontent.com/F1-Buddy/f1buddy-python/main/botPics/f1pythonpfp.png')
        message_embed.set_thumbnail(
        url='https://cdn.discordapp.com/attachments/884602392249770087/1059464532239581204/f1python128.png')
        await interaction.response.defer()
        loop = asyncio.get_running_loop()
        file = await loop.run_in_executor(None, plot_avg_positions, year)
        try:
            message_embed.set_image(url='attachment://image.png')
            await interaction.followup.send(embed=message_embed,file=file)
        except Exception as e:
            message_embed.set_image(url='https://media.tenor.com/lxJgp-a8MrgAAAAd/laeppa-vika-half-life-alyx.gif')
            message_embed.description = f"Error Occured :( {e}"            
            await interaction.followup.send(embed=message_embed)
        loop.close()

async def setup(bot):
    await bot.add_cog(AverageGapTeam(bot))