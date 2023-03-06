import discord
# import mediawiki
import requests
import json
import fastf1
import typing
import pandas as pd
from discord import app_commands
from discord.ext import commands
from emojiid import team_emoji_ids
now = pd.Timestamp.now()


class constructorStandings(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
    @commands.Cog.listener()
    async def on_ready(self):
        print('Constructor Standings cog loaded')  
    @app_commands.command(name='wcc', description='Get constructor standings')
    @app_commands.describe(year = "year")
    
    async def constructorStandings(self, interaction: discord.Interaction, year: typing.Optional[int], round: typing.Optional[int]):
        await interaction.response.defer()
        team_names, team_position, team_points = [], [], []
        url = "https://ergast.com/api/f1/current/constructorStandings.json" if (year == None) or (year < 1957 and year >= now.year) else f"https://ergast.com/api/f1/{year}/constructorStandings.json"
        constructorStandings = requests.get(url)
        response = json.loads(constructorStandings.content)
        year = (response['MRData']['StandingsTable']['season']) 
        constructor_total = (int)(response['MRData']['total'])
        message_embed = discord.Embed(title=f"{year} Constructor Standings", description="").set_thumbnail(url='https://cdn.discordapp.com/attachments/884602392249770087/1059464532239581204/f1python128.png')
        message_embed.colour = discord.Colour.dark_red()
        
        for i in range(0,constructor_total):
            constructor_standings = (response['MRData']['StandingsTable']['StandingsLists'][0]['ConstructorStandings'][i])
            constructor_data = (response['MRData']['StandingsTable']['StandingsLists'][0]['ConstructorStandings'][i]['Constructor'])
            
            try:
                team_names.append((str)(self.bot.get_emoji(team_emoji_ids[constructor_data['name']]))+' ' + constructor_data['name'])
            except:
                team_names.append(constructor_data['name'])
                
            team_position.append(constructor_standings['position'])
            team_points.append(constructor_standings['points'])
            
        message_embed.add_field(name="Position", value='\n'.join(team_position),inline=True)
        message_embed.add_field(name="Team Name", value='\n'.join(team_names),inline=True)
        message_embed.add_field(name="Points", value='\n'.join(team_points),inline=True)
        # send final embed
        await interaction.followup.send(embed=message_embed)

async def setup(bot):
    await bot.add_cog(constructorStandings(bot) # , guilds=[discord.Object(id=884602392249770084)]
                      )