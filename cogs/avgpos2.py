import os
import traceback
import typing
import fastf1
import fastf1.plotting as f1plt
import asyncio
import discord
from discord import app_commands
from discord.ext import commands
import pandas as pd
import matplotlib
matplotlib.use('agg')
from matplotlib import pyplot as plt
from matplotlib.offsetbox import AnnotationBbox, OffsetImage
from matplotlib.ticker import MultipleLocator
from lib.f1font import regular_font, bold_font
import repeated.common as cm
import repeated.embed as em


fastf1.Cache.enable_cache('cache/')

def get_event_data(session_type,year,category):
    # schedule = fastf1.get_event_schedule(year=year)
    schedule = fastf1.get_event_schedule(year=year,include_testing=False)
    first_index = schedule.index[0]
    max_index = cm.latest_completed_index(year)
    first_round = schedule.loc[first_index,'RoundNumber']
    last_round = schedule.loc[max_index,'RoundNumber']
    # print(first_index)
    # print(max_index)
    # print(first_round)
    # print(last_round)
    
    # event = fastf1.get_session(year,first_round,session_type)
    # event.load()
    
    driver_positions = {}
    driver_average = {}
    driver_colors = {}
    driver_racesParticipated = {}
    
    for i in range(first_round,last_round+1):
        event = fastf1.get_session(year,i,session_type)
        event.load(laps=False, telemetry=False, weather=False, messages=False)
        results = event.results
        # print(results)
        
        for driver in event.drivers:
            if (category.name == 'Drivers'):
                currDriver_abbreviation = results.loc[driver,'Abbreviation']
            else:
                currDriver_abbreviation = results.loc[driver,'TeamName']
            
            if driver_positions.get(currDriver_abbreviation) is None:
                driver_positions.update({currDriver_abbreviation:0})

            if driver_racesParticipated.get(currDriver_abbreviation) is None:
                driver_racesParticipated.update({currDriver_abbreviation:0})
            
            if session_type == 'r':
                currDriver_position = results.loc[driver,'ClassifiedPosition']
            else:
                currDriver_position = results.loc[driver,'Position']

                
            currDriver_total = driver_positions.get(currDriver_abbreviation)
            
            if (type(currDriver_position) is str):
                if (currDriver_position.isnumeric()):
                    driver_racesParticipated.update({currDriver_abbreviation:driver_racesParticipated.get(currDriver_abbreviation)+1})
                    driver_positions.update({currDriver_abbreviation:currDriver_total+int(currDriver_position)})
            else:
                driver_racesParticipated.update({currDriver_abbreviation:driver_racesParticipated.get(currDriver_abbreviation)+1})
                driver_positions.update({currDriver_abbreviation:currDriver_total+(currDriver_position)})
            
                
            driver_colors.update({currDriver_abbreviation:results.loc[driver,'TeamColor']})
    # print(driver_positions)
    # print(driver_colors)     
    # print(driver_racesParticipated)   
    for key in driver_positions.keys():
        try:
            driver_average.update({key:driver_positions.get(key)/driver_racesParticipated.get(key)})
        except:
            print('div by 0')
    return driver_average,driver_colors
    # print(driver_colors)

def plot_avg(driver_positions, driver_colors,session_type,year,category,filepath):
    # latest_event_index = cm.latest_completed_index(year)
    plt.clf()
    driver_positions = dict(sorted(driver_positions.items(), key=lambda x: x[1]))
    f1plt._enable_fastf1_color_scheme()
    f1plt.setup_mpl(misc_mpl_mods=False)
    watermark_img = plt.imread('botPics/f1pythoncircular.png') # set directory for later use
    fig, ax = plt.subplots(figsize=(16.8, 10.5)) # create the bar plot and size
    fig.set_facecolor('black')
    ax.set_facecolor('black')
    
    # setting x-axis label, title
    ax.set_xlabel("Position", fontproperties=regular_font, fontsize=20, labelpad=20)
    ax.set_title(f"Average {category.name} {session_type.name} Finish Position {year}", fontproperties=bold_font, fontsize=20, pad=20)
    
    # space between limits for the y-axis and x-axis
    ax.set_ylim(-0.8, len(driver_positions.keys())-0.25)
    ax.set_xlim(0, 20.1)
    ax.invert_yaxis() # invert y axis, top to bottom
    ax.xaxis.set_major_locator(MultipleLocator(1)) # amount x-axis increments by 1

    # remove ticks, keep labels
    ax.xaxis.set_tick_params(labelsize=12)
    ax.yaxis.set_tick_params(labelsize=12)
    ax.set_xticklabels(range(-1,int(max(driver_positions.values()))+6), fontproperties=regular_font, fontsize=20)
    if (category.name == 'Drivers'):
        fontsize = 20
    else:
        fontsize = 10
    ax.set_yticklabels(driver_positions.keys(), fontproperties=bold_font, fontsize=fontsize)
    ax.set_yticks(range(len(driver_positions.keys())))
    ax.tick_params(axis='both', length=0, pad=8, )
    
    # remove all lines, bar the x-axis grid lines
    ax.yaxis.grid(False)
    ax.xaxis.grid(True, color='#191919')
    ax.spines['top'].set_visible(False)
    ax.spines['bottom'].set_visible(False)
    ax.spines['left'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.minorticks_off()
    
    # testing for possible median bars
    # plt.barh("VER", 5, color='none', edgecolor='blue', hatch="/", linewidth=1,alpha=0.6)
    annotated = False
    for driver in driver_positions.keys():
        curr_color = driver_colors.get(driver)
        # print(curr_color)
        # print(curr_color == 'nan')
        if ((curr_color != 'nan') and (curr_color != '')):
            plt.barh(driver, driver_positions.get(driver),color = f'#{curr_color}')
        else:
            if not annotated:
                plt.figtext(0.91, 0.01, "*Some color data is unavailable", ha="center", fontproperties=regular_font)
                annotated = True
            plt.barh(driver, driver_positions.get(driver), color = '#ffffff')
    # add f1buddy pfp
    watermark_box = OffsetImage(watermark_img, zoom=0.2) 
    ab = AnnotationBbox(watermark_box, (-0.115,1.1), xycoords='axes fraction', frameon=False)
    ax.add_artist(ab)
    
    # add text next to it
    ax.text(-0.075,1.085, 'Made by F1Buddy Discord Bot', transform=ax.transAxes,
            fontsize=16,fontproperties=bold_font)
    
    for i, position in enumerate(driver_positions.values()):
        ax.text(position + 0.1, i, f"   {str(round(position,2))}", va='center', fontproperties=regular_font, fontsize=20)
    
    plt.rcParams['savefig.dpi'] = 300
    plt.savefig(filepath)

def get_embed_and_image(year, session_type, category):
    try:
        now = pd.Timestamp.now()
        if (year is None) or (year > now.year):
                year = now.year
                if (cm.currently_offseason()[0]) or (cm.latest_completed_index(now.year) == 0):
                    year = now.year - 1
        latest_event_index = cm.latest_completed_index(year)
        folder_path = f'./cogs/plots/avgpos/{year}/{session_type.name}/{category.name}'
        file_path = f'./cogs/plots/avgpos/{year}/{session_type.name}/{category.name}/{latest_event_index}.png'
        
        # for testing
        # now = pd.Timestamp(year=2020, month=12, day=6).tz_localize('America/New_York')
        if not (os.path.exists(file_path)):
            if not os.path.exists(folder_path):
                os.makedirs(folder_path)
            pos,colors = get_event_data(session_type=session_type.value,year=year, category=category)
            # catch any drawing errors
            try:
                plot_avg(pos,colors,session_type,year,category,file_path)
            except Exception as e:
                return em.ErrorEmbed(error_message=e),None
        file = discord.File(file_path,filename="image.png")
        description = "DNF/DNS excluded from calculation"
        title = f"Average {category.name} {session_type.name} Finish Position {year}"
        return em.Embed(title=title,description=description,image_url='attachment://image.png'), file  
    except Exception as e:
        traceback.print_exc()
        return em.ErrorEmbed(error_message=e), None
 
class AveragePos(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        
    @commands.Cog.listener()
    async def on_ready(self):
        print('Avg Positions cog loaded')
        
    @app_commands.command(name='avgpos', description='See average finish position for driver for race/qualifying throughout the year')
    @app_commands.describe(session_type='Choose between Qualifying or Race')
    @app_commands.choices(session_type=[app_commands.Choice(name="Qualifying", value="q"), app_commands.Choice(name="Race", value="r"),])
    @app_commands.describe(category='Choose between Teams or Drivers')
    @app_commands.choices(category=[app_commands.Choice(name="Drivers", value="Drivers"), app_commands.Choice(name="Teams", value="Teams"),])
    @app_commands.describe(year = "Year")
    async def positions(self, interaction: discord.Interaction, category: app_commands.Choice[str],session_type: app_commands.Choice[str], year: typing.Optional[int]):
        # message_embed = discord.Embed(title=f"Average Finishing Gap between Teams", description="")
        # message_embed.colour = colors.default
        # message_embed.set_author(name='f1buddy',icon_url='https://raw.githubusercontent.com/F1-Buddy/f1buddy-python/main/botPics/f1pythonpfp.png')
        # message_embed.set_thumbnail(
        # url='https://cdn.discordapp.com/attachments/884602392249770087/1059464532239581204/f1python128.png')
        await interaction.response.defer()
        loop = asyncio.get_running_loop()
        dc_embed, file = await loop.run_in_executor(None, get_embed_and_image, year, session_type, category)
        if file != None:
            await interaction.followup.send(embed=dc_embed.embed,file=file)
        else:
            await interaction.followup.send(embed=dc_embed.embed)
        loop.close()

async def setup(bot):
    await bot.add_cog(AveragePos(bot))