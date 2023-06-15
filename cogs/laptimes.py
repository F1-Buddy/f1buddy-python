import discord
import fastf1
import os
import typing
import json
from fastf1 import plotting
from discord import app_commands
from discord.ext import commands
from matplotlib import pyplot as plt
from lib.colors import colors
import pandas as pd

fastf1.Cache.enable_cache('cache/')
plotting.setup_mpl()

class Laptimes(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        print('Laptimes cog loaded')

    @commands.command()
    async def sync(self, ctx) -> None:
        # print("sync command started")
        fmt = await ctx.bot.tree.sync()
        await ctx.send(f'Synced {len(fmt)}')


    
    # driver_list = [
    #     discord.app_commands.Choice(name="HAM",value=1),
    #     discord.app_commands.Choice(name="RUS",value=2),
    #     discord.app_commands.Choice(name="VER",value=3),
    #     discord.app_commands.Choice(name="PER",value=4),
    #     discord.app_commands.Choice(name="LEC",value=5),
    #     discord.app_commands.Choice(name="SAI",value=6),
    #     discord.app_commands.Choice(name="ALO",value=7),
    #     discord.app_commands.Choice(name="OCO",value=8),
    #     discord.app_commands.Choice(name="GAS",value=9),
    #     discord.app_commands.Choice(name="TSU",value=10),
    #     discord.app_commands.Choice(name="BOT",value=11),
    #     discord.app_commands.Choice(name="ZHO",value=12),
    #     discord.app_commands.Choice(name="NOR",value=13),
    #     discord.app_commands.Choice(name="RIC",value=14),
    #     discord.app_commands.Choice(name="MAG",value=15),
    #     discord.app_commands.Choice(name="MSC",value=16),
    #     discord.app_commands.Choice(name="ALB",value=17),
    #     discord.app_commands.Choice(name="LAT",value=18),
    #     discord.app_commands.Choice(name="VET",value=19),
    #     discord.app_commands.Choice(name="STR",value=20),
    #     discord.app_commands.Choice(name="DEV",value=21),
    #     discord.app_commands.Choice(name="SAR",value=22),
    #     discord.app_commands.Choice(name="HUL",value=23),
    #     discord.app_commands.Choice(name="MAZ",value=24),
    #     discord.app_commands.Choice(name="RAI",value=25),
    #     discord.app_commands.Choice(name="PIA",value=26)
    # ]
    @app_commands.command(name='laptimes', description='Compare laptimes of two drivers in a race (2018 onwards)')
    @app_commands.describe(driver1='3 Letter Code for Driver 1')
    @app_commands.describe(driver2='3 Letter Code for Driver 2')
    @app_commands.describe(round='Round name or number (Australia or 3)')
    @app_commands.describe(year = "Year")
    # @app_commands.choices(driver1=driver_list)
    # @app_commands.choices(driver2=driver_list)
    # @app_commands.option
    async def laptimes(self, interaction: discord.Interaction, driver1: str, driver2: str, round:str, year: typing.Optional[int]):
        # make sure inputs uppercase
        driver1 = driver1.upper()
        driver2 = driver2.upper()
        # defer reply for later
        await interaction.response.defer()
        # get current time
        now = pd.Timestamp.now()
        # setup embed
        message_embed = discord.Embed(title="Lap Times", description="")
        message_embed.colour = colors.default
        message_embed.set_thumbnail(
        url='https://cdn.discordapp.com/attachments/884602392249770087/1059464532239581204/f1python128.png')

        # map to hold team colors (correct as of 2022)

        race_year = 0
        
        # get teamcolors json
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
            if (not os.path.exists("cogs/plots/laptime/"+race.date.strftime('%Y-%m-%d_%I%M')+"_laptimes"+driver1+'vs'+driver2+'.png')) and (
                not os.path.exists("cogs/plots/laptime/"+race.date.strftime('%Y-%m-%d_%I%M')+"_laptimes"+driver2+'vs'+driver1+'.png')):

                d1 = race.laps.pick_driver(driver1)
                d2 = race.laps.pick_driver(driver2)
                fig, ax = plt.subplots()
                ax.set_facecolor('gainsboro')
                df = race.results
                # d1number = df.where(df==driver1).dropna(how='all').dropna(axis=1).index[0]
                # d2number = df.where(df==driver2).dropna(how='all').dropna(axis=1).index[0]
                ax.plot(d1['LapNumber'], d1['LapTime'], color=fastf1.plotting.driver_color(driver1), label = driver1)
                ax.plot(d2['LapNumber'], d2['LapTime'], color=fastf1.plotting.driver_color(driver2), label = driver2)
                ax.set_title(racename+ ' '+driver1+" vs "+driver2)
                ax.set_xlabel("Lap Number")
                ax.set_ylabel("Lap Time")
                ax.legend(loc="upper right")
                plt.savefig("cogs/plots/laptime/"+race.date.strftime('%Y-%m-%d_%I%M')+"_laptimes"+driver1+'vs'+driver2+'.png')
                # 
            # try to access the graph
            try:
                file = discord.File("cogs/plots/laptime/"+race.date.strftime('%Y-%m-%d_%I%M')+"_laptimes"+driver1+'vs'+driver2+'.png', filename="image.png")
            
            except Exception as e:
                # try to access the graph by switching driver1 and driver2
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
