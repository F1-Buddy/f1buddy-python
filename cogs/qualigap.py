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
from lib.f1font import regular_font, bold_font
import fastf1.plotting as f1plt
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
def addlabels(x,y,driver_colors, regular_font):
    for i in range(len(x)):
        string = f"+{str(y[i])[0:5].ljust(5,'0')}"
        if (i == 0):
            string = "   Pole"
        elif (string == "+0.000" and i != 0):
            string = "No Time"
        plt.text(min(max(y),5)+0.09, i, string, va = 'center', fontproperties=regular_font)

f1plt._enable_fastf1_color_scheme()
f1plt.setup_mpl(misc_mpl_mods=False)
fig, ax = plt.subplots(figsize=(8.25, 5.5))
fig.set_facecolor('black')
ax.set_facecolor('black')

def quali_gap(round, year):
    # get current time
    now = pd.Timestamp.now()
    event_year = None
    event_round = None
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

        race = fastf1.get_session(event_year, event_round, 'Q')
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
            plt.barh(driver_names, bar_heights,.88, color=driver_colors)
            # label each bar
            addlabels(driver_names, bar_heights, driver_colors, regular_font)
            # set graph limits, try to set ylimit to last driver's delta
            plt.xlim(right=min(max(bar_heights),5), left=0)
            plt.ylim([20,-1])
            # graph setup stuff
            # plt.xticks(rotation=90) 
            ax.minorticks_off()
            # ax.spines['top'].set_visible(False) removes box around chart
            # ax.spines['bottom'].set_visible(False)
            # ax.spines['left'].set_visible(False)
            # ax.spines['right'].set_visible(False)
            plt.grid(visible=False, which='both')
            plt.title(f"Qualifying Gap for {str(race.date.year)+' '+str(race.event.EventName)}",fontproperties=bold_font, pad=20)
            plt.xlabel("Delta (Seconds)",fontproperties=regular_font)
            plt.subplots_adjust(right=0.88,left=0.16,bottom = 0.16,top = 0.78)
            for label in ax.get_xticklabels():
                label.set_fontproperties(regular_font)
            for label in ax.get_yticklabels():
                label.set_fontproperties(bold_font)
            plt.rcParams['savefig.dpi'] = 300
            # save plot
            plt.savefig("cogs/plots/qualigap/"+race.date.strftime('%Y-%m-%d_%I%M')+"_QualiGap"+'.png')
            # plt.show()
            # clear plot
            plt.clf()
            plt.cla()
            plt.close()
            # return
            
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


# quali_gap('baku', 2023)