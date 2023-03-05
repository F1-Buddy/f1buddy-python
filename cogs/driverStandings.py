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
# team_emojis_2 = {
#     "Red Bull":"rb",
#     "Mercedes":"merc",
#     "Ferrari":"sf",
#     "McLaren":"mcl",
#     "Alpine F1 Team":"alp",
#     "Aston Martin":"ast",
#     "Alfa Romeo":"ar",
#     "AlphaTauri":"at",
#     "Williams":"w_",
#     "Haas F1 Team":"haas"
# }
team_emojis_ids = {
    "Red Bull":1081767515790770247,
    "Mercedes":1081767514620571749,
    "Ferrari":1081767510019411978,
    "McLaren":1081767512733126736,
    "Alpine F1 Team":1081767507209224192,
    "Aston Martin":1081767508287176734,
    "Alfa Romeo":1081767504617148417,
    "AlphaTauri":1081767505539903508,
    "Williams":1081767613283176579,
    "Haas F1 Team":1081767511424520313
}


class driverStandings(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
    @commands.Cog.listener()
    async def on_ready(self):
        print('Driver Standings cog loaded')
    @app_commands.command(name='wdc', description='Get driver standings')
    @app_commands.describe(year = "WDC name")
    
    async def driverStandings(self, interaction: discord.Interaction, year: typing.Optional[int]):
        driver_name, driver_position, driver_points = [], [], []
        await interaction.response.defer()
        url = "https://ergast.com/api/f1/current/driverStandings.json" if (year == None) or (year < 1957) or (year > now.year) else f"https://ergast.com/api/f1/{year}/driverStandings.json"
        driverStandings = requests.get(url)
        response = json.loads(driverStandings.content)
        year = (response['MRData']['StandingsTable']['season']) 
        message_embed = discord.Embed(title=f"{year} Driver Standings", description="").set_thumbnail(url='https://cdn.discordapp.com/attachments/884602392249770087/1059464532239581204/f1python128.png')
        message_embed.colour = discord.Colour.dark_red()
        
        # print("emojis:")
        # for i in self.bot.emojis:
        #     print(i)
            
        for i in range(0,20):
            driver_standings = (response['MRData']['StandingsTable']['StandingsLists'][0]['DriverStandings'][i])
            driver_data = (response['MRData']['StandingsTable']['StandingsLists'][0]['DriverStandings'][i]['Driver'])
            driver_constructor = (response['MRData']['StandingsTable']['StandingsLists'][0]['DriverStandings'][i]['Constructors'][0])
            driver_position.append(driver_standings['position'])
            driver_name.append((str)(self.bot.get_emoji(team_emojis_ids[driver_constructor['name']])) + " " + driver_data['givenName'] + ' ' + driver_data['familyName'])
            driver_points.append(driver_standings['points'])
        
        driver_positions_string = '\n'.join(driver_position)
        driver_names_string = '\n'.join(driver_name)
        driver_points_string = '\n'.join(driver_points)
        
        message_embed.add_field(name="Position", value= driver_positions_string,inline=True)
        message_embed.add_field(name="Driver", value=driver_names_string,inline=True)
        message_embed.add_field(name="Points", value=driver_points_string,inline=True)
        # send final embed
        await interaction.followup.send(embed=message_embed)

async def setup(bot):
    await bot.add_cog(driverStandings(bot))