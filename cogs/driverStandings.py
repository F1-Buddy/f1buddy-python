import discord
import mediawiki
import requests
import json
import fastf1
import typing
import pandas as pd
from discord import app_commands
from discord.ext import commands

class driverStandings(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        print('Standings cog loaded')
        
    @app_commands.command(name='wcc', description='Get driver info')
    @app_commands.describe(year = "WCC name")
    # @app_commands.describe(driver="Driver")
    # @app_commands.choices(driver = driver_list)
    
    async def driverStandings(self, interaction: discord.Interaction, year: typing.Optional[int]):
        await interaction.response.defer()
        
        now = pd.Timestamp.now()
        if ((year == None) or (year < 1957 and year > now.year)):
            url = "https://ergast.com/api/f1/current/driverStandings.json"
        else:
            url = "https://ergast.com/api/f1/" + (str)(year) + "/driverStandings.json"
            
        driverStandings = requests.get(url)
        response = json.loads(driverStandings.content)
        
        driver_names, driver_position, driver_points, = [], [], []
        message_embed = discord.Embed(title="Driver Standings", description="")
        message_embed.set_thumbnail(
            url='https://cdn.discordapp.com/attachments/884602392249770087/1059464532239581204/f1python128.png')
        
        for i in range(0,10):
            driver_standings = (response['MRData']['StandingsTable']['StandingsLists'][0]['DriverStandings'][i])
            driver_data = (response['MRData']['StandingsTable']['StandingsLists'][0]['DriverStandings'][i]['Driver'])
            driver_team = (response['MRData']['StandingsTable']['StandingsLists'][0]['DriverStandings'][i]['Driver']['Constructors'][i])
            driver_names.append(driver_data['givenName'])
            driver_names.append(driver_data['familyName'])
            driver_position.append(driver_standings['position'])
            driver_points.append(driver_standings['points'])
            
        message_embed.add_field(name="Position", value='\n'.join(team_position),inline=True)
        message_embed.add_field(name="Driver", value='\n'.join(team_names),inline=True)
        message_embed.add_field(name="Points", value='\n'.join(team_points),inline=True)
        
        # send final embed
        await interaction.followup.send(embed=message_embed)

async def setup(bot):
    await bot.add_cog(Standings(bot)
    # , guilds=[discord.Object(id=884602392249770084)]
    )