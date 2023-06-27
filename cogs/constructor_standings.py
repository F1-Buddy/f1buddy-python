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

class ConstructorStandings(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
    @commands.Cog.listener()
    async def on_ready(self):
        print('Constructor Standings cog loaded')  
    @app_commands.command(name='wcc', description='Get constructor standings')
    @app_commands.describe(year = "Constructor standings year")
    # @app_commands.describe(round = "Constructor standings round")
    
    async def ConstructorStandings(self, interaction: discord.Interaction, year: typing.Optional[int]):
        await interaction.response.defer()
        ergast = Ergast()
        team_names, team_position, team_points = [], [], []
        year = datetime.datetime.now().year if (year == None) or (year < 1957) or (year >= now.year) else year # set year depending on input
        
        constructor_standings = ergast.get_constructor_standings(season=year).content[0]
        for index in range(len(constructor_standings)):
            position = constructor_standings.iloc[index]['position']
            points = constructor_standings.iloc[index]['points']
            if points == int(points):
                points = int(points)
            team_position.append(position)
            team_points.append(points)
            names = constructor_standings.iloc[index]['constructorName']
            try:
                team_names.append((str)(self.bot.get_emoji(team_emoji_ids[names])) + ' ' + names)
            except:
                team_names.append(names)
        
        message_embed = discord.Embed(title=f"{year} Constructor Standings", description="").set_thumbnail(url='https://cdn.discordapp.com/attachments/884602392249770087/1059464532239581204/f1python128.png')
        message_embed.set_author(name='f1buddy',icon_url='https://raw.githubusercontent.com/F1-Buddy/f1buddy-python/main/botPics/f1pythonpfp.png')
        message_embed.colour = colors.default
        
        # Sets McLaren's position to EX, due to their disqualification in the 2007 constructor's championship. 
        if (year == 2007):
            team_position[10] = "EX"
        
        # replaces commas in list with newline
        team_position = '\n'.join(map(str, team_position))
        team_names = '\n'.join(team_names)
        team_points = '\n'.join(map(str, team_points))
        
        message_embed.add_field(name="Position", value=team_position,inline=True)
        message_embed.add_field(name="Team Name", value=team_names,inline=True)
        message_embed.add_field(name="Points", value=team_points,inline=True)
        # send final embed
        await interaction.followup.send(embed=message_embed)

async def setup(bot):
    await bot.add_cog(ConstructorStandings(bot) # , guilds=[discord.Object(id=884602392249770084)]
                      )
