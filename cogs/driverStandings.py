import discord
import mediawiki
import requests
import json
import fastf1
import typing
import pandas as pd
from discord import app_commands
from discord.ext import commands
now = pd.Timestamp.now()
driver_name, driver_position, driver_points = [], [], []
# team_emojis = {
#     "Red Bull":"<:rb:1081767515790770247>",
#     "Mercedes":"<:merc:1081767514620571749>",
#     "Ferrari":"<:sf:1081767510019411978>",
#     "McLaren":"<:mcl:1081767512733126736>",
#     "Alpine F1 Team":"<:alp:1081767507209224192>",
#     "Aston Martin":"<:ast:1081767508287176734>",
#     "Alfa Romeo":"<:ar:1081767504617148417>",
#     "AlphaTauri":"<:at:1081767505539903508>",
#     "Williams":"<:w_:1081767613283176579>",
#     "Haas F1 Team":"<:haas:1081767511424520313>"
# }


class driverStandings(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
    @commands.Cog.listener()
    async def on_ready(self):
        print('Driver Standings cog loaded')
    @app_commands.command(name='wdc', description='Get driver standings')
    @app_commands.describe(year = "WDC name")
    
    async def driverStandings(self, interaction: discord.Interaction, year: typing.Optional[int]):
        await interaction.response.defer()
        url = "https://ergast.com/api/f1/current/driverStandings.json" if (year == None) or (year < 1957) or (year > now.year) else f"https://ergast.com/api/f1/{year}/driverStandings.json"
        driverStandings = requests.get(url)
        response = json.loads(driverStandings.content)
        year = (response['MRData']['StandingsTable']['season']) 
        message_embed = discord.Embed(title=f"{year} Driver Standings", description="").set_thumbnail(url='https://cdn.discordapp.com/attachments/884602392249770087/1059464532239581204/f1python128.png')
        message_embed.colour = discord.Colour.dark_red()
        
        emojis = []
        for i in guild:
            for j in guild.emojis:
                emojis.append(j)
        print(emojis)
        for i in range(0,20):
            driver_standings = (response['MRData']['StandingsTable']['StandingsLists'][0]['DriverStandings'][i])
            driver_data = (response['MRData']['StandingsTable']['StandingsLists'][0]['DriverStandings'][i]['Driver'])
            driver_constructor = (response['MRData']['StandingsTable']['StandingsLists'][0]['DriverStandings'][i]['Constructors'][0])
            driver_position.append(driver_standings['position'])
            driver_name.append(team_emojis[driver_constructor['name']] + " " + driver_data['givenName'] + ' ' + driver_data['familyName'])
            driver_points.append(driver_standings['points'])
            
        message_embed.add_field(name="Position", value='\n'.join(driver_position),inline=True)
        message_embed.add_field(name="Driver", value='\n'.join(driver_name),inline=True)
        message_embed.add_field(name="Points", value='\n'.join(driver_points),inline=True)
        # send final embed
        await interaction.followup.send(embed=message_embed)

async def setup(bot):
    await bot.add_cog(driverStandings(bot) # , guilds=[discord.Object(id=884602392249770084)]
                      )