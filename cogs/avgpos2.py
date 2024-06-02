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

def get_event_data(session_type,year,category, ignore_dnfs):
    # schedule = fastf1.get_event_schedule(year=year)
    schedule = fastf1.get_event_schedule(year=year,include_testing=False)
    first_index = schedule.index[0]
    if (session_type.value == 'q'):
        max_index = cm.latest_quali_completed_index(year)
    else:
        max_index = cm.latest_completed_index(year)
    
    first_round = schedule.loc[first_index,'RoundNumber']
    if (session_type.value == 'r'):
        last_round = cm.latest_completed_index(year)
    else:
        last_round = cm.latest_quali_completed_index(year)
    # print(first_index)
    print(max_index)
    print(first_round)
    print(last_round)
    
    # event = fastf1.get_session(year,first_round,session_type)
    # event.load()
    
    driver_positions = {}
    driver_average = {}
    driver_colors = {}
    driver_racesParticipated = {}
    
    for i in range(first_round,last_round + 1):
        try:
            event = fastf1.get_session(year,i,session_type.value)
            event.load(laps=False, telemetry=False, weather=False, messages=False)
            results = event.results
            # print(results)
            
            for driver in event.drivers:
                if (category.name == 'Drivers'):
                    currDriver_abbreviation = results.loc[driver,'Abbreviation']
                else:
                    currDriver_abbreviation = results.loc[driver,'TeamName']
                
                # default value to 0 if not in dictionary
                if driver_positions.get(currDriver_abbreviation) is None:
                    driver_positions.update({currDriver_abbreviation:0})

                if driver_racesParticipated.get(currDriver_abbreviation) is None:
                    driver_racesParticipated.update({currDriver_abbreviation:0})
                
                if session_type.value == 'r':
                    currDriver_position = results.loc[driver,'ClassifiedPosition']
                else:
                    currDriver_position = results.loc[driver,'Position']
                    
                currDriver_total = driver_positions.get(currDriver_abbreviation)
                
                if isinstance(currDriver_position,str) and currDriver_position.isnumeric():
                    currDriver_position = int(currDriver_position)

                # filter based on ignore_dnfs input
                skip_driver = False
                if ignore_dnfs == 'True':
                    if not ('finished' in results.loc[driver,'Status'].lower() or '+' in results.loc[driver,'Status'].lower()):
                        skip_driver = True
                elif ignore_dnfs == 'Mechanical':
                    # ignore mechanical retirement statuses like Gearbox, Engine, Brakes, etc
                    # **** Unknown if there are other statuses that are mechanical failures, these are just the ones I know of ****
                    mechanical_failure_reasons = ["Gearbox", "Engine", "Brakes", "Rear wing"]
                    if (results.loc[driver,'Status'] in mechanical_failure_reasons):
                        skip_driver = True
                    
                # add race if not to be skipped
                if not skip_driver:
                    if isinstance(currDriver_position,str):
                        currDriver_position = results.loc[driver,'Position']
                    # stroll 2023 singapore solution (withdrew, position = numpy nan, classified = W)
                    if str(currDriver_position) != "nan":
                        driver_racesParticipated.update({currDriver_abbreviation:driver_racesParticipated.get(currDriver_abbreviation)+1})
                        driver_positions.update({currDriver_abbreviation:currDriver_total+currDriver_position})

                # was messing with current driver colors --> Looks ugly and makes it hard to compare teammates
                # if u find it hard to read, skill issue
                
                # now = pd.Timestamp.now()
                # if year == now.year:
                #     driver_colors.update({currDriver_abbreviation:fastf1.plotting.driver_color(currDriver_abbreviation)})
                # else:
                driver_colors.update({currDriver_abbreviation:results.loc[driver,'TeamColor']})
                
        except KeyError:
            print("session not completed")
    # print(driver_positions)
    # print(driver_colors)     
    # print(driver_racesParticipated)   
    for key in driver_positions.keys():
        try:
            driver_average.update({key:driver_positions.get(key)/driver_racesParticipated.get(key)})
        except:
            traceback.print_exc()
    return driver_average,driver_colors
    # print(driver_colors)

def plot_avg(driver_positions, driver_colors,session_type,year,category,filepath,ignore_dnfs):
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
    title_string = f"Average {category.name} {session_type.name} Finish Position {year}"
    if ignore_dnfs == 'True':
        title_string += " (DNF/DNS Excluded)"
    elif ignore_dnfs == 'Mechanical':
        title_string += " (Mechanical DNFs Excluded)"
    else:
        title_string += " (DNFS Included)"
    ax.set_title(title_string, fontproperties=bold_font, fontsize=20, pad=20)
    
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
            if ("#" in curr_color):
                plt.barh(driver, driver_positions.get(driver),color = curr_color)
            else:
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
    # plt.show()
    plt.savefig(filepath)

def get_embed_and_image(year, session_type, category, ignore_dnfs):
    try:
        # now = pd.Timestamp.now()
        try:
            year = cm.check_year(year,False,session_type.value == 'q')
        except cm.YearNotValidException as e:
            return em.ErrorEmbed(title=f"Invalid Input: {year}",error_message=e), None
        except:
            return em.ErrorEmbed(error_message=traceback.format_exc()), None
        latest_event_index = cm.latest_completed_index(year)
        folder_path = f'./cogs/plots/avgpos/{year}/{session_type.name}/{category.name}/{ignore_dnfs}'
        file_path = f'./cogs/plots/avgpos/{year}/{session_type.name}/{category.name}/{ignore_dnfs}/{latest_event_index}.png'
        
        # for testing
        # now = pd.Timestamp(year=2020, month=12, day=6).tz_localize('America/New_York')
        if not (os.path.exists(file_path)):
            if not os.path.exists(folder_path):
                os.makedirs(folder_path)
            pos,colors = get_event_data(session_type=session_type,year=year, category=category, ignore_dnfs=ignore_dnfs)
            # catch any drawing errors
            try:
                plot_avg(pos,colors,session_type,year,category,file_path,ignore_dnfs)
            except Exception as e:
                traceback.print_exc()
                return em.ErrorEmbed(error_message=e),None
        file = discord.File(file_path,filename="image.png")
        if (ignore_dnfs == 'True'):
            description = "DNF/DNS excluded from calculation"
        elif (ignore_dnfs == 'Mechanical'):
            description = "Mechanical DNFs excluded from calculation"
        else:
            description = "DNFs included in calculation"
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
    @app_commands.describe(ignore_dnfs='Ignore DNFs')
    @app_commands.choices(ignore_dnfs=[app_commands.Choice(name="All", value="True"), 
                                        app_commands.Choice(name="Mechanical", value="Mechanical"),
                                        app_commands.Choice(name="No", value="False"),])
    @app_commands.describe(year = "Year")
    
    async def positions(self, interaction: discord.Interaction, category: app_commands.Choice[str],session_type: app_commands.Choice[str], ignore_dnfs: app_commands.Choice[str],year: typing.Optional[int]):
        await interaction.response.defer()
        try:
            loop = asyncio.get_running_loop()
            dc_embed, file = await loop.run_in_executor(None, get_embed_and_image, year, session_type, category, ignore_dnfs.value)
            if file != None:
                await interaction.followup.send(embed=dc_embed.embed,file=file)
            else:
                await interaction.followup.send(embed=dc_embed.embed)
        except:
            traceback.print_exc()
        loop.close()

async def setup(bot):
    await bot.add_cog(AveragePos(bot))