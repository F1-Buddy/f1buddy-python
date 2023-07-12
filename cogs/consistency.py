import asyncio
import fastf1
from matplotlib import pyplot as plt, ticker
import pandas as pd
from lib.drivernames import driver_names
from lib.f1font import regular_font, bold_font
from lib.colors import colors
import discord
from discord import app_commands
from discord.ext import commands
lap_colors = []

def convert_to_code(driver):
    if driver in driver_names.values():
        return driver
    driver_code = driver_names.get(driver)
    if driver_code is None:
        raise ValueError(f"Unknown driver: {driver}")
    return driver_code

def laptime_consistency(driver):
    driver_code = convert_to_code(driver)
    print(driver_code)
    session = fastf1.get_session(2023, 1, 'R')
    session.load(telemetry=True, laps=True)
    

    specified_driver = 'ALO'
    driver_laps = session.laps.pick_driver(specified_driver)
    print(driver_laps['LapTime'])
    print(driver_laps['LapTime'].dt.total_seconds())
    print(driver_laps['LapNumber'])
    final_lap_number = driver_laps['LapNumber'].max()
    mean_lap_time = driver_laps['LapTime'].mean().total_seconds()
    std_lap_time = driver_laps['LapTime'].std()

    # for lap_time in driver_laps['LapTime'].dt.total_seconds():
    #     if lap_time > mean_lap_time:
    #         lap_colors.append('blue')  
    #     else:
    #         lap_colors.append('green')  

    fig, ax = plt.subplots()
    # fig.set_facecolor('black')
    # ax.set_facecolor('black')
    try:
        plt.scatter(driver_laps['LapNumber'], driver_laps['LapTime'].dt.total_seconds())
    except Exception as e:
        print(f"Error {e}")
        # ax.plot(driver_laps['LapNumber'], driver_laps['LapTime'].dt.total_seconds(), color='blue', label=specified_driver)
        
    ax.axhline(mean_lap_time, color='red', linestyle='--', label='Mean Lap Time')
    # ax.plot(driver_laps['LapNumber'], driver_laps['LapTime'].dt.total_seconds(), color='blue', label=specified_driver)

    y_ticks = ax.get_yticks()
    converted_labels = []
    for tick in y_ticks:
        minutes = int(tick // 60)
        seconds = int(tick % 60)
        converted_labels.append("{:02d}:{:02d}".format(minutes, seconds))
    
    ax.set_yticklabels(converted_labels)
    ax.set_title(f"{specified_driver} Laptime Consistency", fontproperties=bold_font)
    ax.set_xlabel("Lap Number", fontproperties=regular_font, labelpad=10)
    ax.set_ylabel("Lap Time", fontproperties=regular_font, labelpad=10)
    for label in ax.get_xticklabels() + ax.get_yticklabels():
        label.set_fontproperties(regular_font)
    plt.rcParams['savefig.dpi'] = 300
    plt.savefig(f"cogs/plots/consistency/consistency{session.date.strftime('%Y-%m-%d_%I%M')}_{specified_driver}.png") # save plot
    
    consistency_embed = discord.Embed(title=f"{specified_driver} Laptime Consistency", description="")
    consistency_embed.colour = colors.default
    consistency_embed.set_author(name='f1buddy',icon_url='https://raw.githubusercontent.com/F1-Buddy/f1buddy-python/main/botPics/f1pythonpfp.png')
    consistency_embed.set_thumbnail(url='https://cdn.discordapp.com/attachments/884602392249770087/1059464532239581204/f1python128.png')
    try:
        file = discord.File(f"cogs/plots/consistency/consistency{session.date.strftime('%Y-%m-%d_%I%M')}_{specified_driver}.png", filename="image.png")
    except Exception as e:
        print(e)
        consistency_embed.set_footer(text=e)
        
    return consistency_embed, file

class Consistency(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
    @commands.Cog.listener()
    async def on_ready(self):
        print('Laptime consistency cog loaded')
        
    @app_commands.command(name='consistency', description='Plot driver laptime consistency')
    @app_commands.describe(driver = "Driver name/code")
    async def consistency(self, interaction: discord.Interaction, driver:str):
        await interaction.response.defer()
        print("a")
        loop = asyncio.get_running_loop()
        print("a")
        
        print("a")
        try:
            print("a")
            consistency_embed, file = await loop.run_in_executor(None, laptime_consistency, driver)
            print("b")
            consistency_embed.set_image(url='attachment://image.png')
            await interaction.followup.send(embed=consistency_embed, file=file)
        except Exception as e:
            consistency_embed.set_image(url='https://media.tenor.com/lxJgp-a8MrgAAAAd/laeppa-vika-half-life-alyx.gif')
            consistency_embed.description = f"Error Occured :( {e}"            
            await interaction.followup.send(embed=consistency_embed)
        loop.close()

async def setup(bot):
    await bot.add_cog(Consistency(bot))