import asyncio
import discord
import typing
import pandas as pd
from fastf1.ergast import Ergast
import fastf1
from discord import app_commands
from discord.ext import commands
from lib.emojiid import team_emoji_ids
from lib.colors import colors
import repeated.common as cm
import repeated.embed as em
import traceback

now = pd.Timestamp.now().tz_localize('America/New_York')

def get_constructor_standings(self, year):
    ergast = Ergast()
    team_names, team_position, team_points = [], [], []

    # fixed not working during new year off season but still not great
    # prefer if (year <= 1957) or (year >= now.year) created a separate error embed asking for valid input
    try:
        year = cm.check_year(year,False,False)
    except cm.YearNotValidException as e:
        return em.ErrorEmbed(title=f"Invalid Input: {year}",error_message=e)
    except:
        return em.ErrorEmbed(error_message=traceback.format_exc())
    
    constructor_standings = ergast.get_constructor_standings(season=year).content[0]
    for index in range(len(constructor_standings)):
        position = constructor_standings.iloc[index]['position']
        points = constructor_standings.iloc[index]['points']
        if points == int(points):
            points = int(points)
        team_position.append(position)
        team_points.append(points)
        name = constructor_standings.iloc[index]['constructorName']
        try:
            emoji = (str)(self.bot.get_emoji(team_emoji_ids[name]))
            if (now.year != year and index == 0):
                name = f"{constructor_standings.iloc[index]['constructorName']} :crown:"
            team_names.append(emoji + ' ' + name)
        except:
            team_names.append(name)
    
    dc_embed = em.Embed(title=f"{year} Constructor Standings")
    
    # Sets McLaren's position to EX, due to their disqualification in the 2007 constructor's championship. 
    if (year == 2007):
        team_position[10] = "EX"
    
    # replaces commas in list with newline
    team_position = '\n'.join(map(str, team_position))
    team_names = '\n'.join(team_names)
    team_points = '\n'.join(map(str, team_points))
    
    dc_embed.embed.add_field(name="Position", value=team_position,inline=True)
    dc_embed.embed.add_field(name="Team Name", value=team_names,inline=True)
    dc_embed.embed.add_field(name="Points", value=team_points,inline=True)
    return dc_embed
        
class constructor_standings(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
    @commands.Cog.listener()
    async def on_ready(self):
        print('Constructor Standings cog loaded')  
    @app_commands.command(name='wcc', description='Get constructor standings')
    @app_commands.describe(year = "Constructor standings year")
    
    async def constructor_standings(self, interaction: discord.Interaction, year: typing.Optional[int]):
        await interaction.response.defer()
        loop = asyncio.get_running_loop()
        # run query and build embed
        constructor_standings_embed = await loop.run_in_executor(None, get_constructor_standings, self, year)
        # send embed
        await interaction.followup.send(embed = constructor_standings_embed.embed)
        loop.close()

async def setup(bot):
    await bot.add_cog(constructor_standings(bot) # , guilds=[discord.Object(id=884602392249770084)]
                      )
