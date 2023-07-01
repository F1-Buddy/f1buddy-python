import json
import discord
import asyncio
import fastf1
import os
import typing
from discord import app_commands
from discord.ext import commands
from matplotlib import pyplot as plt
import matplotlib
matplotlib.use('agg')
from lib.colors import colors
import pandas as pd
import fastf1.plotting as f1plt
from matplotlib.ticker import (MultipleLocator, AutoMinorLocator)

fastf1.Cache.enable_cache('cache/')

# setup embed
message_embed = discord.Embed(title="Qualifying Gap to Leader", description="")
message_embed.colour = colors.default
message_embed.set_author(name='f1buddy',icon_url='https://raw.githubusercontent.com/F1-Buddy/f1buddy-python/main/botPics/f1pythonpfp.png')
message_embed.set_thumbnail(
url='https://cdn.discordapp.com/attachments/884602392249770087/1059464532239581204/f1python128.png')

# get timedelta and return formatted string
def td_to_laptime(td):
    td_microseconds = td.microseconds
    td_seconds = td.seconds
    td_minutes = td_seconds // 60
    td_seconds = str(td_seconds % 60).zfill(2)
    td_thousandths = str(td_microseconds)[:-3].ljust(3, '0')
    return f"{td_minutes}:{td_seconds}.{td_thousandths}"

# add labels to each bar
def addlabels(x,y):
    for i in range(len(x)):
        plt.text(i, y[0]-0.02, f"+{str(y[i])[0:5].ljust(5,'0')}", ha = 'center',rotation=90,)

f1plt._enable_fastf1_color_scheme()
f1plt.setup_mpl(misc_mpl_mods=False)
fig, ax = plt.subplots()

def quali_gap(round, year):
    # get current time
    now = pd.Timestamp.now()

    try:
        # year given is invalid
        try:
            year = int(year)
        except:
            year = now.year
        if (year > now.year | year < 2018):
            try:
                race = fastf1.get_session(now.year, round, 'Q')
            except:
                race = fastf1.get_session(now.year, (int)(round), 'Q')
            race.load()
            racename = '' + str(race.date.year)+' '+str(race.event.EventName)
        
        # use given year
        else:
            try:
                race = fastf1.get_session(year, round, 'Q')
            except:
                race = fastf1.get_session(year, (int)(round), 'Q')
            race.load()
            racename = '' + str(race.date.year)+' '+str(race.event.EventName)
        resultsTable = race.results
        # check if graph already exists, if not create it
        message_embed.description = racename
        if (not os.path.exists("cogs/plots/qualigap/"+race.date.strftime('%Y-%m-%d_%I%M')+"_QualiGap"+'.png')):

            # get fastest lap time in session
            fastest_lap = resultsTable.loc[resultsTable.index[0],'Q3']

            # get all driver names
            driver_names = [resultsTable.loc[i,'Abbreviation'] for i in resultsTable.index]
            driver_colors = []
            bar_heights = []
            for i in resultsTable.index:
                # get driver colors
                if (year == now.year):
                    driver_color = f1plt.driver_color(resultsTable.loc[i,'Abbreviation'])
                    driver_colors.append(driver_color)
                else:
                    driver_color = f"#{resultsTable.loc[i,'TeamColor']}"
                    driver_colors.append(driver_color)
                # get each drivers' qualifying delta to leader
                if (str(resultsTable.loc[i,'Q3']) != "NaT"):
                    bar_heights.append((resultsTable.loc[i,'Q3']-fastest_lap).total_seconds())
                elif (str(resultsTable.loc[i,'Q2']) != "NaT"):
                    bar_heights.append((resultsTable.loc[i,'Q2']-fastest_lap).total_seconds())
                elif (str(resultsTable.loc[i,'Q1']) != "NaT"):
                    bar_heights.append((resultsTable.loc[i,'Q1']-fastest_lap).total_seconds())
                else:
                    # no time was set
                    bar_heights.append(0.0)
            
            # plot each delta as a bar
            plt.bar(driver_names, bar_heights, color=driver_colors)
            # label each bar
            addlabels(driver_names, bar_heights)
            # set graph limits, try to set ylimit to last driver's delta
            plt.ylim(bottom=min(max(bar_heights),5), top=0)
            # graph setup stuff
            plt.xticks(rotation=90) 
            ax.minorticks_off()
            # plt.grid(visible=False, which='both')
            plt.title(f"Qualifying Gap for {str(race.date.year)+' '+str(race.event.EventName)}",y=1.16,fontdict = {'fontsize' : '16'})
            plt.ylabel("Delta (Seconds)")
            plt.xlabel("Driver")
            plt.subplots_adjust(left=0.16,bottom = 0.16,top = 0.78)
            plt.rcParams['savefig.dpi'] = 300
            # save plot
            plt.savefig("cogs/plots/qualigap/"+race.date.strftime('%Y-%m-%d_%I%M')+"_QualiGap"+'.png')
            # clear plot
            plt.clf()
            plt.cla()
            plt.close()
        # try to access the graph
        try:
            file = discord.File("cogs/plots/qualigap/"+race.date.strftime('%Y-%m-%d_%I%M')+"_QualiGap"+'.png', filename="image.png")
            message_embed.set_footer(text="")
            return file
        
        except Exception as e:
            print(e)
            message_embed.set_footer(text=e)
    # 
    except Exception as e:
        print(e)
        message_embed.set_footer(text = e)


class QualiGap(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        print('QualiGap cog loaded')

    @app_commands.command(name='qualigap', description='See driver position changes over the race')
    @app_commands.describe(round='Round name or number (Australia or 3)')
    @app_commands.describe(year = "Year")
    async def QualiGap(self, interaction: discord.Interaction, round:str, year: typing.Optional[int]):
        # defer reply for later
        await interaction.response.defer()
        loop = asyncio.get_running_loop()
        # run results query and build embed
        file = await loop.run_in_executor(None, quali_gap, round, year)

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
    await bot.add_cog(QualiGap(bot))
