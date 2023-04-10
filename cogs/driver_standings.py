import discord
import requests
import json
import typing
import pandas as pd
from discord import app_commands
from discord.ext import commands
from lib.emojiid import team_emoji_ids
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
        driver_name, driver_position, driver_points = [], [], []
        await interaction.response.defer()
        # get standings JSON
        url = "https://ergast.com/api/f1/current/driverStandings.json" if (year == None) or (year < 1957) or (year >= now.year) else f"https://ergast.com/api/f1/{year}/driverStandings.json"
        driverStandings = requests.get(url)
        response = json.loads(driverStandings.content)
        driver_total = (int)(response['MRData']['total'])
        # get season year
        year = (response['MRData']['StandingsTable']['season']) 
        # set embed color and title
        message_embed = discord.Embed(title=f"{year} Driver Standings", description="").set_thumbnail(url='https://cdn.discordapp.com/attachments/884602392249770087/1059464532239581204/f1python128.png')
        message_embed.colour = discord.Colour.dark_red()
            
        for i in range(0,driver_total):
            driver_standings = (response['MRData']['StandingsTable']['StandingsLists'][0]['DriverStandings'][i])
            driver_data = (response['MRData']['StandingsTable']['StandingsLists'][0]['DriverStandings'][i]['Driver'])
            driver_constructor = (response['MRData']['StandingsTable']['StandingsLists'][0]['DriverStandings'][i]['Constructors'][0])
                
            try:
                if (driver_total <= 24):
                    driver_name.append((str)(self.bot.get_emoji(team_emoji_ids[driver_constructor['name']]))+ ' ' + driver_data['givenName'] + ' ' + driver_data['familyName'])
                else:
                    driver_name.append((str)(self.bot.get_emoji(team_emoji_ids[driver_constructor['name']]))+ ' ' + driver_data['givenName'][0] + "." + ' ' + driver_data['familyName'])
            except:
                driver_name.append((driver_data['givenName']) + ' ' + (driver_data['familyName']))

            driver_position.append(driver_standings['position'])
            driver_points.append(driver_standings['points'])
        
        driver_positions_string = '\n'.join(driver_position)
        driver_names_string = '\n'.join(driver_name)
        if (len(driver_names_string) >= 1024):
            driver_names_string = driver_names_string[:1024 - len(driver_names_string) - 1] + '.'
        driver_points_string = '\n'.join(driver_points)
        
        message_embed.add_field(name="Position", value= driver_positions_string,inline=True)
        message_embed.add_field(name="Driver", value=driver_names_string,inline=True)
        message_embed.add_field(name="Points", value=driver_points_string,inline=True)
        # send final embed
        await interaction.followup.send(embed=message_embed)

async def setup(bot):
    await bot.add_cog(DriverStandings(bot))
