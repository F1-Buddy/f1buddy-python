import asyncio
import discord
import fastf1
import os
import typing
from fastf1 import plotting
from discord import app_commands
from discord.ext import commands
from matplotlib import pyplot as plt
from lib.colors import colors
import pandas as pd

fastf1.Cache.enable_cache('cache/')

# get current time
now = pd.Timestamp.now()
# set up pyplot
plotting.setup_mpl()
plt.grid(True, linestyle='--')
# setup embed
message_embed = discord.Embed(title="Lap Times", description="")
message_embed.colour = colors.default
message_embed.set_author(name='f1buddy',icon_url='https://raw.githubusercontent.com/F1-Buddy/f1buddy-python/main/botPics/f1pythonpfp.png')
message_embed.set_thumbnail(
url='https://cdn.discordapp.com/attachments/884602392249770087/1059464532239581204/f1python128.png')

def laptime_results(driver1: str, driver2: str, round:str, year: typing.Optional[int]):
    try:
        # year given is invalid
        try:
            year = int(year)
        except:
            year = now.year
        if (year > now.year | year < 2018):
            try:
                race = fastf1.get_session(now.year, round, 'R')
            except:
                race = fastf1.get_session(now.year, (int)(round), 'R')
            race.load()
            racename = '' + str(race.date.year)+' '+str(race.event.EventName)
        
        # use given year
        else:
            try:
                race = fastf1.get_session(year, round, 'R')
            except:
                race = fastf1.get_session(year, (int)(round), 'R')
            race.load()
            racename = '' + str(race.date.year)+' '+str(race.event.EventName)
        # check if graph already exists, if not create it
        if (not os.path.exists("cogs/plots/laptime/"+race.date.strftime('%Y-%m-%d_%I%M')+"_laptimes"+driver1+'vs'+driver2+'.png')) and (
            not os.path.exists("cogs/plots/laptime/"+race.date.strftime('%Y-%m-%d_%I%M')+"_laptimes"+driver2+'vs'+driver1+'.png')):
            
            # get driver data
            d1 = race.laps.pick_driver(driver1)
            d2 = race.laps.pick_driver(driver2)
            fig, ax = plt.subplots()
            ax.set_facecolor('gainsboro')
            # plot laptimes
            ax.plot(d1['LapNumber'], d1['LapTime'], color=fastf1.plotting.driver_color(driver1), label = driver1)
            ax.plot(d2['LapNumber'], d2['LapTime'], color=fastf1.plotting.driver_color(driver2), label = driver2)
            # pyplot setup
            ax.set_title(racename+ ' '+driver1+" vs "+driver2)
            ax.set_xlabel("Lap Number")
            ax.set_ylabel("Lap Time")
            ax.legend(loc="upper right")
            plt.rcParams['savefig.dpi'] = 300
            # save plot
            plt.savefig("cogs/plots/laptime/"+race.date.strftime('%Y-%m-%d_%I%M')+"_laptimes"+driver1+'vs'+driver2+'.png')
            # reset plot just in case
            plt.clf()
            plt.cla()
            plt.close()
        # try to access the graph
        try:
            file = discord.File("cogs/plots/laptime/"+race.date.strftime('%Y-%m-%d_%I%M')+"_laptimes"+driver1+'vs'+driver2+'.png', filename="image.png")
            message_embed.description = '' + str(race.date.year)+' '+str(race.event.EventName)+ '\n' + driver1+" vs "+driver2
            message_embed.set_footer(text='')
            return file
        
        except Exception as e:
            # try to access the graph by switching driver1 and driver2 in filename
            try:
                file = discord.File("cogs/plots/laptime/"+race.date.strftime('%Y-%m-%d_%I%M')+"_laptimes"+driver2+'vs'+driver1+'.png', filename="image.png")
                message_embed.description = '' + str(race.date.year)+' '+str(race.event.EventName)+ '\n' + driver1+" vs "+driver2
                message_embed.set_footer(text='')
                print("Swapped drivers around and found a file")
                return file
            # file does not exist and could not be created
            except:
                message_embed.set_footer(text="Likely an unsupported input (year/round) was given \n *(2018+)*")
    # 
    except Exception as e:
        print(e)
        message_embed.set_footer(text = "Unknown Error occured")



class Laptimes(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        print('Laptimes cog loaded')



    @app_commands.command(name='laptimes', description='Compare laptimes of two drivers in a race (2018 onwards)')
    
    # inputs
    @app_commands.describe(driver1='3 Letter Code for Driver 1')
    @app_commands.describe(driver2='3 Letter Code for Driver 2')
    @app_commands.describe(round='Round name or number (Australia or 3)')
    @app_commands.describe(year = "Year")
    
    # command
    async def laptimes(self, interaction: discord.Interaction, driver1: str, driver2: str, round:str, year: typing.Optional[int]):
        # defer reply for later
        await interaction.response.defer()
        # make sure inputs uppercase
        driver1 = driver1.upper()
        driver2 = driver2.upper()

        loop = asyncio.get_running_loop()
        # run results query and build embed
        file = await loop.run_in_executor(None, laptime_results, driver1, driver2, round, year)

        # send embed
        try:
            message_embed.set_image(url='attachment://image.png')
            await interaction.followup.send(embed=message_embed,file=file)
        except:
            message_embed.description = "Error Occured :("            
            await interaction.followup.send(embed=message_embed)
        loop.close()


async def setup(bot):
    await bot.add_cog(Laptimes(bot))
