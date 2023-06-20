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
        # get current time
        now = pd.Timestamp.now()
        # setup embed
        message_embed = discord.Embed(title="Lap Times", description="")
        message_embed.colour = colors.default
        message_embed.set_thumbnail(
        url='https://cdn.discordapp.com/attachments/884602392249770087/1059464532239581204/f1python128.png')

        try:
            # year given is invalid
            if (year == None or year > now.year or year < 2018):
                # check if round was given as string or int
                try:
                    race = fastf1.get_session(now.year, round, 'R')
                except:
                    race = fastf1.get_session(now.year, (int)(round), 'R')
                race.load()
                racename = '' + str(race.date.year)+' '+str(race.event.EventName)
            
            # use given year
            else:
                # check if round was given as string or int
                try:
                    race = fastf1.get_session(now.year, round, 'R')
                except:
                    race = fastf1.get_session(now.year, (int)(round), 'R')
                racename = '' + str(race.date.year)+' '+str(race.event.EventName)
            # check if graph already exists, if not create it
            race.load()
            if (not os.path.exists("cogs/plots/laptime/"+race.date.strftime('%Y-%m-%d_%I%M')+"_laptimes"+driver1+'vs'+driver2+'.png')) and (
                not os.path.exists("cogs/plots/laptime/"+race.date.strftime('%Y-%m-%d_%I%M')+"_laptimes"+driver2+'vs'+driver1+'.png')):
                # set up pyplot
                plotting.setup_mpl()
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
            
            except Exception as e:
                # try to access the graph by switching driver1 and driver2 in filename
                print(e)
                try:
                    file = discord.File("cogs/plots/laptime/"+race.date.strftime('%Y-%m-%d_%I%M')+"_laptimes"+driver2+'vs'+driver1+'.png', filename="image.png")
                    print("Swapped drivers around and found a file")
                # file does not exist and could not be created
                except:
                    message_embed.set_footer(text="Likely an unsupported input (year/round) was given \n *(2018+)*")
        # 
        except Exception as e:
            print(e)
            message_embed.set_footer(text = "Error occured")


        # send embed
        try:
            message_embed.description = '' + str(race.date.year)+' '+str(race.event.EventName)+ '\n' + driver1+" vs "+driver2
            message_embed.set_image(url='attachment://image.png')
            await interaction.followup.send(embed=message_embed,file=file)
        except:
            message_embed.description = "Error Occured :("            
            await interaction.followup.send(embed=message_embed)


async def setup(bot):
    await bot.add_cog(Laptimes(bot))
