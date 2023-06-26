import datetime
import discord
import requests
import json
import typing
import pandas as pd
from fastf1.ergast import Ergast
from discord import app_commands
from discord.ext import commands
from lib.emojiid import team_emoji_ids
from lib.colors import colors

now = pd.Timestamp.now()

class DriverStandings(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
    @commands.Cog.listener()
    async def on_ready(self):
        print('Driver Standings cog loaded')
    @app_commands.command(name='wdc', description='Get driver standings')
    @app_commands.describe(year = "Standings year")
    
    async def DriverStandings(self, interaction: discord.Interaction, year: typing.Optional[int]):
        await interaction.response.defer()
        driver_name, driver_position, driver_points = [], [], []
        ergast = Ergast()
        year = datetime.datetime.now().year if (year == None) or (year < 1957) or (year >= now.year) else year # set year depending on input
                
        # go through each
        driver_standings = ergast.get_driver_standings(season=year).content[0]
        for index in range(len(driver_standings)):
            position = driver_standings.iloc[index]['position']
            name = f"{driver_standings.iloc[index]['givenName']} {driver_standings.iloc[index]['familyName']}"
            points = driver_standings.iloc[index]['points']
            driver_position.append(position)
            driver_points.append(points)
            constructor_names = driver_standings.iloc[index]['constructorNames']
            constructor_names_string = '\n'.join(map(str, constructor_names))
            try:
                driver_name.append((str)(self.bot.get_emoji(team_emoji_ids[constructor_names_string])) + " " + name)
            except:
                driver_name.append(name)
        
        # sets embed color and title
        message_embed = discord.Embed(title=f"{year} Driver Standings", description="").set_thumbnail(url='https://cdn.discordapp.com/attachments/884602392249770087/1059464532239581204/f1python128.png')
        message_embed.set_author(name='f1buddy',icon_url='https://raw.githubusercontent.com/F1-Buddy/f1buddy-python/main/botPics/f1pythonpfp.png')
        message_embed.colour = colors.default

        # replaces commas in list with newline
        driver_positions_string = '\n'.join(map(str, driver_position))
        driver_names_string = '\n'.join(driver_name)
        if len(driver_names_string) >= 1024:
            driver_names_string = driver_names_string[:1024 - len(driver_names_string) - 1] + '.'
        driver_points_string = '\n'.join(map(str, driver_points))
        
        # discord embed columns
        message_embed.add_field(name="Position", value= driver_positions_string,inline=True)
        message_embed.add_field(name="Driver", value=driver_names_string,inline=True)
        message_embed.add_field(name="Points", value=driver_points_string,inline=True)
        await interaction.followup.send(embed=message_embed)

async def setup(bot):
    await bot.add_cog(DriverStandings(bot))