import discord
import fastf1
import os
import typing
import pandas as pd
from fastf1 import plotting
from discord import app_commands
from discord.ext import commands
from matplotlib import pyplot as plt

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


    
    driver_list = [
        discord.app_commands.Choice(name="HAM",value=1),
        discord.app_commands.Choice(name="RUS",value=2),
        discord.app_commands.Choice(name="VER",value=3),
        discord.app_commands.Choice(name="PER",value=4),
        discord.app_commands.Choice(name="LEC",value=5),
        discord.app_commands.Choice(name="SAI",value=6),
        discord.app_commands.Choice(name="ALO",value=7),
        discord.app_commands.Choice(name="OCO",value=8),
        discord.app_commands.Choice(name="GAS",value=9),
        discord.app_commands.Choice(name="TSU",value=10),
        discord.app_commands.Choice(name="BOT",value=11),
        discord.app_commands.Choice(name="ZHO",value=12),
        discord.app_commands.Choice(name="NOR",value=13),
        discord.app_commands.Choice(name="RIC",value=14),
        discord.app_commands.Choice(name="MAG",value=15),
        discord.app_commands.Choice(name="MSC",value=16),
        discord.app_commands.Choice(name="ALB",value=17),
        discord.app_commands.Choice(name="LAT",value=18),
        discord.app_commands.Choice(name="VET",value=19),
        discord.app_commands.Choice(name="STR",value=20)
    ]
    @app_commands.command(name='laptimes', description='Compare laptimes of two drivers in a race (2018 onwards)')
    @app_commands.describe(driver1='Drivers')
    @app_commands.describe(driver2='Drivers')
    @app_commands.describe(round='Round Number')
    @app_commands.describe(year = "Year")
    @app_commands.choices(driver1=driver_list)
    @app_commands.choices(driver2=driver_list)
    # @app_commands.option
    async def laptimes(self, interaction: discord.Interaction, driver1: discord.app_commands.Choice[int], driver2: discord.app_commands.Choice[int], round:int, year: typing.Optional[int]):
        # defer reply for later
        await interaction.response.defer()
        # get current time
        now = pd.Timestamp.now()
        # setup embed
        message_embed = discord.Embed(title="Lap Times", description="")
        message_embed.set_thumbnail(
        url='https://cdn.discordapp.com/attachments/884602392249770087/1059464532239581204/f1python128.png')

        # map to hold team colors (correct as of 2022)
        team_colors = {
        'LEC':'red',
        'SAI':'red',
        'HAM':'turquoise',
        'RUS':'turquoise',
        'VER':'mediumblue',
        'PER':'mediumblue',
        'OCO':'fuchsia',
        'ALO':'fuchsia',
        'NOR':'darkorange',
        'RIC':'darkorange',
        'VET':'green',
        'STR':'green',
        'ALB':'royalblue',
        'LAT':'royalblue',
        'BOT':'maroon',
        'ZHO':'maroon',
        'MAG':'white',
        'MSC':'white',
        'TSU':'lightsteelblue',
        'GAS':'lightsteelblue'
        }

        race_year = 0
        

        try:
            # year given is invalid
            if (year == None or year > now.year or year < 2018):
                # print("year not given/year given invalid")
                race = fastf1.get_session(now.year, round, 'R')
                race_year = now.year
                while (race.date > now):
                    race_year -= 1
                    race = fastf1.get_session(race_year, round, 'R')
                racename = '' + str(race.date.year)+' '+str(race.event.EventName)
            
            # use given year
            else:
                race = fastf1.get_session(year, round, 'R')
                race_year = year
                racename = '' + str(race.date.year)+' '+str(race.event.EventName)
            # check if graph already exists, if not create it
            if (not os.path.exists("cogs/plots/"+str(race_year)+"laptimes"+str(round)+str(driver1.name)+'vs'+str(driver2.name)+'.png')) and (not os.path.exists("cogs/plots/"+str(race_year)+"laptimes"+str(round)+str(driver2.name)+'vs'+str(driver1.name)+'.png')):
                race.load()
                d1 = race.laps.pick_driver(str(driver1.name))
                d2 = race.laps.pick_driver(str(driver2.name))
                fig, ax = plt.subplots()
                ax.plot(d1['LapNumber'], d1['LapTime'], color=team_colors[str(driver1.name)])
                ax.plot(d2['LapNumber'], d2['LapTime'], color=team_colors[str(driver2.name)])
                ax.set_title(racename+ ' '+str(driver1.name)+" vs "+str(driver2.name))
                ax.set_xlabel("Lap Number")
                ax.set_ylabel("Lap Time")
                plt.savefig("cogs/plots/"+str(race_year)+"laptimes"+str(round)+str(driver1.name)+'vs'+str(driver2.name)+'.png')
            # try to access the graph
            try:
                file = discord.File("cogs/plots/"+str(race_year)+"laptimes"+str(round)+str(driver1.name)+'vs'+str(driver2.name)+'.png', filename="image.png")
            
            except:
                # try to access the graph by switching driver1 and driver2
                try:
                    file = discord.File("cogs/plots/"+str(race_year)+"laptimes"+str(round)+str(driver2.name)+'vs'+str(driver1.name)+'.png', filename="image.png")
                # file does not exist and could not be created
                except:
                    message_embed.set_footer(text="Likely an unsupported input (year/round) was given \n *(2018+)*")
        # 
        except:
            message_embed.set_footer(text = "Invalid round # was given!")


        # send embed
        try:
            message_embed.description = '' + str(race.date.year)+' '+str(race.event.EventName)+ '\n' + str(driver1.name)+" vs "+str(driver2.name)
            message_embed.set_image(url='attachment://image.png')
            await interaction.followup.send(embed=message_embed,file=file)
        except:
            message_embed.description = "Error Occured :("            
            await interaction.followup.send(embed=message_embed)


async def setup(bot):
    await bot.add_cog(Laptimes(bot))