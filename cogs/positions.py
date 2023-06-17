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
import fastf1.plotting as f1plt
from matplotlib import pyplot as plt
from matplotlib.ticker import (MultipleLocator, AutoMinorLocator)

fastf1.Cache.enable_cache('cache/')


class Positions(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        print('Positions cog loaded')

    @app_commands.command(name='positions', description='See driver position changes over the race')
    @app_commands.describe(round='Round name or number (Australia or 3)')
    @app_commands.describe(year = "Year")
    async def laptimes(self, interaction: discord.Interaction, round:str, year: typing.Optional[int]):
        
        f1plt.setup_mpl()
        f1plt.setup_mpl(misc_mpl_mods=False)
        fig, ax = plt.subplots(figsize=(8.0, 4.9))
        plt.ylabel("Position")
        plt.xlabel("Lap")
        plt.tight_layout()
        plt.subplots_adjust(right=0.85,top = 0.89)
        ax.set_facecolor('black')
        ax.set_ylim([21, 0])
        ax.set_yticks(range(1,21))
        # defer reply for later
        await interaction.response.defer()
        # get current time
        now = pd.Timestamp.now()
        # setup embed
        message_embed = discord.Embed(title="Driver Positions", description="")
        message_embed.colour = colors.default
        message_embed.set_thumbnail(
        url='https://cdn.discordapp.com/attachments/884602392249770087/1059464532239581204/f1python128.png')

        try:
            # year given is invalid
            if (year == None or year > now.year or year < 2018):
                try:
                    race = fastf1.get_session(now.year, round, 'R')
                except:
                    race = fastf1.get_session(now.year, (int)(round), 'R')
                race.load()
                racename = '' + str(race.date.year)+' '+str(race.event.EventName)
            
            # use given year
            else:
                try:
                    race = fastf1.get_session(now.year, round, 'R')
                except:
                    race = fastf1.get_session(now.year, (int)(round), 'R')
                racename = '' + str(race.date.year)+' '+str(race.event.EventName)
            # check if graph already exists, if not create it
            race.load()
            if (not os.path.exists("cogs/plots/positions/"+race.date.strftime('%Y-%m-%d_%I%M')+"_positions"+'.png')):

                for driver in race.drivers:
                    driver_laps = race.laps.pick_driver(driver)
                    driver_name = driver_laps["Driver"].iloc[0]
                    driver_color = f1plt.driver_color(driver_name)
                    plt.plot(driver_laps["LapNumber"],driver_laps["Position"], color = driver_color, label = driver_name)



                ax.legend(bbox_to_anchor=(1.0, 1.02), fontsize=9.2)
                ax.minorticks_off()
                ax.xaxis.set_major_locator(MultipleLocator(5))
                ax.xaxis.set_minor_locator(MultipleLocator(1))
                plt.title('Position Changes during '+racename)
                plt.grid(visible=False, which='both')
                plt.rcParams['savefig.dpi'] = 300
                plt.savefig("cogs/plots/positions/"+race.date.strftime('%Y-%m-%d_%I%M')+"_positions"+'.png')
                plt.clf()
                plt.cla()
                plt.close()
                # 
            # try to access the graph
            try:
                file = discord.File("cogs/plots/positions/"+race.date.strftime('%Y-%m-%d_%I%M')+"_positions"+'.png', filename="image.png")
            
            except Exception as e:
                print(e)
                message_embed.set_footer(text="Likely an unsupported input (year/round) was given \n *(2018+)*")
        # 
        except Exception as e:
            print(e)
            message_embed.set_footer(text = "Error occured")


        # send embed
        try:
            message_embed.description = racename
            message_embed.set_image(url='attachment://image.png')
            await interaction.followup.send(embed=message_embed,file=file)
        except:
            message_embed.description = "Error Occured :("            
            await interaction.followup.send(embed=message_embed)


async def setup(bot):
    await bot.add_cog(Positions(bot))
