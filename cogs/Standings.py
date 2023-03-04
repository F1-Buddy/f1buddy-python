import discord
import mediawiki
import requests
import json
import fastf1
import typing
import pandas as pd
from discord import app_commands
from discord.ext import commands

class Standings(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        print('Standings cog loaded')
        
    @app_commands.command(name='wcc', description='Get driver info')
    @app_commands.describe(year = "WCC name")
    # @app_commands.describe(driver="Driver")
    # @app_commands.choices(driver = driver_list)
    
    async def Standings(self, interaction: discord.Interaction, year: typing.Optional[int]):
        await interaction.response.defer()
        
        now = pd.Timestamp.now()
        if ((year == None) or (year < 1957 and year > now.year)):
            url = "https://ergast.com/api/f1/current/constructorStandings.json"
        else:
            url = "https://ergast.com/api/f1/" + (str)(year) + "/constructorStandings.json"
            
        constructorStandings = requests.get(url)
        response = json.loads(constructorStandings.content)
        
        team_names, team_position, team_points = [], [], []
        # setup embed
        message_embed = discord.Embed(title="Constructors Standings", description="")
        message_embed.set_thumbnail(
            url='https://cdn.discordapp.com/attachments/884602392249770087/1059464532239581204/f1python128.png')
        
        for i in range(0,10):
            standings_data = (response['MRData']['StandingsTable']['StandingsLists'][0]['ConstructorStandings'][i])
            team_data = (response['MRData']['StandingsTable']['StandingsLists'][0]['ConstructorStandings'][i]['Constructor'])
            team_names.append(team_data['name'])
            team_position.append(standings_data['position'])
            team_points.append(standings_data['points'])
            
        message_embed.add_field(name="Position", value='\n'.join(team_position),inline=True)
        message_embed.add_field(name="Team Name", value='\n'.join(team_names),inline=True)
        message_embed.add_field(name="Points", value='\n'.join(team_points),inline=True)
        
        # print(standings_data['DriverStandings'])

        
        # send final embed
        await interaction.followup.send(embed=message_embed)

async def setup(bot):
    await bot.add_cog(Standings(bot)
    # , guilds=[discord.Object(id=884602392249770084)]
    )