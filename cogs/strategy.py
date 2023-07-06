import discord
import typing
import pandas as pd
import fastf1
import fastf1.plotting
from matplotlib import pyplot as plt
from discord import app_commands
from discord.ext import commands
from lib.colors import colors


class Strategy(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
    @commands.Cog.listener()
    async def on_ready(self):
        print('Strategy cog loaded')  
    @app_commands.command(name='strategy', description='View driver strategy over race ')
    @app_commands.describe(year = "Strategy")
    
    async def Strategy(self, interaction: discord.Interaction, year:int, round:str):
        await interaction.response.defer()
        message_embed = discord.Embed(title=f"Strategy Overview", description="").set_thumbnail(url='https://cdn.discordapp.com/attachments/884602392249770087/1059464532239581204/f1python128.png')
        message_embed.colour = colors.default
        now = pd.Timestamp.now()
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
            laps = race.laps

            drivers = race.drivers
            print(drivers)

            drivers = [race.get_driver(driver)["Abbreviation"] for driver in drivers]
            print(drivers)

            stints = laps[["Driver", "Stint", "Compound", "LapNumber"]]
            stints = stints.groupby(["Driver", "Stint", "Compound"])
            stints = stints.count().reset_index()
            stints = stints.rename(columns={"LapNumber": "StintLength"})
            print(stints)

            fig, ax = plt.subplots(figsize=(5, 10))

            for driver in drivers:
                driver_stints = stints.loc[stints["Driver"] == driver]

                previous_stint_end = 0
                for idx, row in driver_stints.iterrows():
                    # each row contains the compound name and stint length
                    # we can use these information to draw horizontal bars
                    plt.barh(
                        y=driver,
                        width=row["StintLength"],
                        left=previous_stint_end,
                        color=fastf1.plotting.COMPOUND_COLORS[row["Compound"]],
                        edgecolor="black",
                        fill=True
                    )

                    previous_stint_end += row["StintLength"]

            plt.title(f"{year} {racename} Strategies")
            plt.xlabel("Lap Number")
            plt.grid(False)
            # invert the y-axis so drivers that finish higher are closer to the top
            ax.invert_yaxis()

            # sphinx_gallery_defer_figures

            ###############################################################################
            # Plot aesthetics
            ax.spines['top'].set_visible(False)
            ax.spines['right'].set_visible(False)
            ax.spines['left'].set_visible(False)

            plt.tight_layout()
            plt.show()
            plt.savefig("cogs/plots/strategy/"+race.date.strftime('%Y-%m-%d_%I%M')+"strategy"+'.png')
            # clear plot
            plt.clf()
            plt.cla()
            plt.close()
            # try to access the graph
            try:
                file = discord.File("cogs/plots/strategy/"+race.date.strftime('%Y-%m-%d_%I%M')+"strategy"+'.png', filename="image.png")
                message_embed.set_image(url='attachment://image.png')
                await interaction.followup.send(embed=message_embed,file=file)
            except Exception as e:
                print(e)
                message_embed.set_footer(text=e)
        except Exception as e:
            print(e)
            message_embed.set_footer(text = e)

async def setup(bot):
    await bot.add_cog(Strategy(bot) # , guilds=[discord.Object(id=884602392249770084)]
                      )