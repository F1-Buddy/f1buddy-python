import asyncio
import traceback
import discord
import typing
import pandas as pd
from fastf1.ergast import Ergast
from discord import app_commands
from discord.ext import commands
from lib.emojiid import team_emoji_ids
from lib.colors import colors
# import fastf1
import repeated.common as cm
import repeated.embed as em

now = pd.Timestamp.now().tz_localize('America/New_York')
        
def get_driver_standings(self, year):
    driver_name, driver_position, driver_points = [], [], []
    ergast = Ergast()
    
    # fixed not working during new year off season but still not great
    # prefer if (year <= 1957) or (year >= now.year) created a separate error embed asking for valid input
    try:
        year = cm.check_year(year,False,False)
    except cm.YearNotValidException as e:
        return em.ErrorEmbed(title=f"Invalid Input: {year}",error_message=e).embed
    except:
        return em.ErrorEmbed(error_message=traceback.format_exc()).embed
    
    # go through each
    driver_standings = ergast.get_driver_standings(season=year).content[0]
    for index in range(len(driver_standings)):
        position = driver_standings.iloc[index]['position']
        if index == 0 and year != now.year:
            name = f"{driver_standings.iloc[index]['givenName']} {driver_standings.iloc[index]['familyName']} :crown:"
        else:
            name = f"{driver_standings.iloc[index]['givenName']} {driver_standings.iloc[index]['familyName']}"
        points = (driver_standings.iloc[index]['points'])
        if points == int(points):
            points = int(points)
        driver_position.append(position)
        driver_points.append(points)
        constructor_name = driver_standings.iloc[index]['constructorNames']
        # if driver has drove for multiple teams
        constructor_name = constructor_name[0]
        
        # COME UP WITH A BETTER SYSTEM
        # maybe store names in list instead, check if too long and edit list from there, create string after
        try:
            # discord runs out of character space after 21 drivers
            if (len(driver_standings) <= 22):
                emoji_id = team_emoji_ids.get(constructor_name)
                emoji = self.bot.get_emoji(emoji_id)
                if emoji:
                    driver_name.append(f"{emoji} {name}")
                else:
                    driver_name.append(name)
            elif (len(driver_standings) >= 23 and len(driver_standings) <= 24):
                # shorten first name to first initial to save space
                first_name = driver_standings.iloc[index]['givenName'][0] 
                last_name = driver_standings.iloc[index]['familyName']
                emoji_id = team_emoji_ids.get(constructor_name)
                emoji = self.bot.get_emoji(emoji_id)
                if emoji:
                    driver_name.append(f"{emoji} {first_name}. {last_name}")
                else:
                    driver_name.append(name)
            elif (len(driver_standings) > 24 and len(driver_standings) < 27):
                # removed first name when over 26 drivers
                last_name = driver_standings.iloc[index]['familyName']
                emoji_id = team_emoji_ids.get(constructor_name)
                emoji = self.bot.get_emoji(emoji_id)
                if emoji:
                    driver_name.append(f"{emoji} {last_name}")
                else:
                    driver_name.append(name)
            elif (len(driver_standings) > 26):
                driver_name.append(name)
        except KeyError as ke:
            driver_name.append(name)
            print(ke)
    
    # sets embed color and title
    message_embed = discord.Embed(title=f"{year} Driver Standings", description="").set_thumbnail(url='https://cdn.discordapp.com/attachments/884602392249770087/1059464532239581204/f1python128.png')
    message_embed.set_author(name='f1buddy',icon_url='https://raw.githubusercontent.com/F1-Buddy/f1buddy-python/main/botPics/f1pythonpfp.png')
    message_embed.colour = colors.default

    # replaces commas in list with newline
    driver_position = '\n'.join(map(str, driver_position))
    driver_name = '\n'.join(driver_name)
    if len(driver_name) >= 1024:
        driver_name = driver_name[:1024 - len(driver_name) - 1] + '.'
    driver_points = '\n'.join(map(str, driver_points))
    
    # discord embed columns
    message_embed.add_field(name="Position", value= driver_position,inline=True)
    message_embed.add_field(name="Driver", value=driver_name,inline=True)
    message_embed.add_field(name="Points", value=driver_points,inline=True)
    return message_embed
        
class driver_standings(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
    @commands.Cog.listener()
    async def on_ready(self):
        print('Driver Standings cog loaded')
    @app_commands.command(name='wdc', description='Get driver standings')
    @app_commands.describe(year = "Standings year")
    
    async def driver_standings(self, interaction: discord.Interaction, year: typing.Optional[int]):
        await interaction.response.defer()
        loop = asyncio.get_running_loop()
        # run query and build embed
        driver_standings_embed = await loop.run_in_executor(None, get_driver_standings, self, year)
        driver_standings_embed.set_author(name='f1buddy',icon_url='https://raw.githubusercontent.com/F1-Buddy/f1buddy-python/main/botPics/f1pythonpfp.png')
        # send embed
        await interaction.followup.send(embed = driver_standings_embed)
        loop.close()

async def setup(bot):
    await bot.add_cog(driver_standings(bot))