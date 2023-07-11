import asyncio
import datetime
import typing
import discord
import fastf1
import unidecode
import pandas as pd
import country_converter as coco
from cogs.avgpos import avg_pos
from lib.colors import colors
from lib.drivernames import driver_names
from discord import app_commands
from discord.ext import commands
from lib.emojiid import team_emoji_ids
from fastf1.ergast import Ergast
from datetime import datetime
from lib.emojiid import nation_dictionary
fastf1.Cache.enable_cache('cache/')
now = pd.Timestamp.now()
current_year = datetime.now().year
title=''
is_team, is_nation = False, False

def head_to_head(self, driver1_code, driver2_code, sessiontype):
    driver1_code = driver1_code.upper()
    driver2_code = driver2_code.upper()
    sessiontype = str(sessiontype.name)
    message_embed = discord.Embed(title=f"Head to Head {sessiontype} Stats", description="").set_thumbnail(url='https://cdn.discordapp.com/attachments/884602392249770087/1059464532239581204/f1python128.png')   
    message_embed.set_author(name='f1buddy', icon_url='https://raw.githubusercontent.com/F1-Buddy/f1buddy-python/main/botPics/f1pythonpfp.png')
    message_embed.colour = colors.default 
    
    ergast = Ergast()
    nationality_dict = nation_dictionary()
    driver_info = ergast.get_driver_info(season=current_year)
    driver_dictionary, team_dictionary = {}, {}
    for _, row in driver_info.iterrows():
        given_name = unidecode.unidecode(row['givenName'])
        family_name = unidecode.unidecode(row['familyName'])
        full_name = given_name + ' ' + family_name
        nationality = row['driverNationality']
        driver_dictionary[full_name] = nationality
    session = fastf1.get_session(current_year, 1, sessiontype)
    session.load()
    session = session.results
    for _, row in session.iterrows():
        code = row['Abbreviation']
        team_name = row['TeamName']
        team_dictionary[code] = team_name
    driver_positions, driver_teams = avg_pos(sessiontype)
    code_to_name = {code: name for name, code in driver_names.items()}  # Mapping of three-letter codes to full names
    wins, losses = 0, 0
    driver_name, driver_name1, driver_name2, team_emojis, score = [], [], [], [], []

    try:       
        if driver1_code != 'NULL' and driver2_code != 'NULL':
            driver1 = code_to_name.get(driver1_code)
            driver2 = code_to_name.get(driver2_code)
            if driver1 and driver2:
                driver1_positions = driver_positions.get(driver1)
                driver2_positions = driver_positions.get(driver2)
                if driver1_positions and driver2_positions:
                    for i in range(len(driver1_positions)):
                        if driver1_positions[i] < driver2_positions[i]:
                            wins += 1
                        elif driver1_positions[i] > driver2_positions[i]:
                            losses += 1
                    try:
                        if driver1_code in team_dictionary and driver2_code in team_dictionary:
                            emoji1 = team_emoji_ids.get(team_dictionary[driver1_code])
                            emoji2 = team_emoji_ids.get(team_dictionary[driver2_code])
                            if emoji1 and emoji2:
                                driver_name1.append(f"{(str)(self.bot.get_emoji(emoji1))} {driver1}")
                                score.append(f"`{wins}` - `{losses}`")
                                driver_name2.append(f"{(str)(self.bot.get_emoji(emoji2))} {driver2}")
                            elif driver1 in driver_dictionary and driver2 in driver_dictionary:
                                nationality1 = driver_dictionary[driver1]
                                nationality2 = driver_dictionary[driver2]
                                emoji1 = ":flag_" + \
                                    (coco.convert(
                                    names=nationality_dict[nationality1][0], to='ISO2')).lower()+":"
                                emoji2 = ":flag_" + \
                                    (coco.convert(
                                    names=nationality_dict[nationality2][0], to='ISO2')).lower()+":"
                                driver_name1.append(f"{(str)(self.bot.get_emoji(emoji1))} {driver1}")
                                score.append(f"`{wins}` `{losses}`")
                                driver_name2.append(f"{(str)(self.bot.get_emoji(emoji2))} {driver2}")
                        else:
                            print(f"{driver1} vs {driver2}: {wins}-{losses}")
                            driver_name.append(f"{driver1} vs {driver2}: {wins}-{losses}")
                    except Exception as e:
                        print(f"Error: {e}")
                else:
                    print(f"Insufficient data for the head-to-head comparison between {driver1} and {driver2}.")
            else:
                print("hhh")
                print("Invalid driver code.")
                
            driver_name1 = '\n'.join(driver_name1)
            driver_name2 = '\n'.join(driver_name2)
            score = '\n'.join(score)
            message_embed.add_field(name=driver1_code, value=driver_name1,inline=True)
            message_embed.add_field(name='Score', value=score,inline=True)
            message_embed.add_field(name=driver2_code, value=driver_name2,inline=True)
            
        elif (driver1_code != 'NULL' and driver2_code == 'NULL') or (driver1_code == 'NULL' and driver2_code != 'NULL'):
            if driver1_code == 'NULL':
                temp = driver1_code
                driver1_code = driver2_code
                driver2_code = temp
                print(f"{driver1_code} xx {driver2_code}")
            driver1 = code_to_name.get(driver1_code)
            driver1_positions = driver_positions.get(driver1)
            
            if driver1_positions:
                for driver2, positions in driver_positions.items():
                    if driver2 != driver1:
                        wins, losses = 0, 0
                        driver2_code = driver_names.get(driver2)
                        print(driver2_code)
                        for i in range(len(driver1_positions)):
                            if driver1_positions[i] < positions[i]:
                                wins += 1
                            elif driver1_positions[i] > positions[i]:
                                losses += 1
                        try:
                            if driver1_code in team_dictionary:
                                print("a"+driver1_code)
                            if driver2_code in team_dictionary:
                                print("b"+driver2_code)
                            if driver1_code in team_dictionary and driver2_code in team_dictionary:
                                print(team_dictionary[driver1_code])
                                emoji1 = team_emoji_ids.get(team_dictionary[driver1_code])
                                emoji2 = team_emoji_ids.get(team_dictionary[driver2_code])
                                print("tsaedqw")
                                if emoji1 and emoji2:
                                    driver_name1.append(f" {driver1} `{wins}`")
                                    driver_name2.append(f"{(str)(self.bot.get_emoji(emoji2))} {driver2} `{wins}` - `{losses}`")
                                    is_team = True
                                elif driver1 in driver_dictionary and driver2 in driver_dictionary:
                                    nationality1 = driver_dictionary[driver1]
                                    nationality2 = driver_dictionary[driver2]
                                    emoji1 = ":flag_" + \
                                        (coco.convert(names=nationality_dict[nationality1][0], to='ISO2')).lower()+":"
                                    emoji2 = ":flag_" + \
                                        (coco.convert(names=nationality_dict[nationality2][0], to='ISO2')).lower()+":"
                                    print("tttt")
                                    driver_name1.append(f"{emoji1} {driver1}    `{wins}`")
                                    driver_name2.append(f"  `{losses}` {emoji2} {driver2}")
                                    print(driver_name)
                                    is_nation = True
                            else:
                                print(f"{driver1} vs {driver2}: {wins}-{losses}")
                                driver_name.append(f"{driver1} vs {driver2}: {wins}-{losses}")
                        except Exception as e:
                            print(f"Error: {e}")
                            wins, losses = 0, 0
            else:
                print("Invalid driver code.")
            driver_name1 = '\n'.join(driver_name1)
            driver_name2 = '\n'.join(driver_name2)
            if is_team:   
                emoji1 = team_emoji_ids.get(team_dictionary[driver1_code])
                message_embed.add_field(name=f"{(str)(self.bot.get_emoji(emoji1))} {driver1} vs.", value=driver_name2,inline=True)
                message_embed.set_footer(text =f'Format of score: {driver1} vs. Driver',icon_url="https://cdn.discordapp.com/attachments/884602392249770087/1059464532239581204/f1python128.png")
            elif is_nation:
                nationality1 = driver_dictionary[driver1]
                emoji1 = ":flag_" + \
                (coco.convert(names=nationality_dict[nationality1][0], to='ISO2')).lower()+":"
                message_embed.add_field(name=f"{(str)(self.bot.get_emoji(emoji1))} {driver1}", value=driver_name1,inline=True)
            else:
                message_embed.add_field(name="Driver 1", value=driver_name2,inline=True)
    
        elif driver1_code == 'NULL' and driver2_code == 'NULL':
            unique_pairs = set()
            for i, (driver1, team1) in enumerate(zip(driver_positions, driver_teams)):
                for j, (driver2, team2) in enumerate(zip(driver_positions, driver_teams)):
                    if i != j and (driver2, driver1) not in unique_pairs and team1 == team2:
                        unique_pairs.add((driver1, driver2))
                        wins, losses = 0, 0
                        driver1_positions = driver_positions[driver1]
                        driver2_positions = driver_positions[driver2]
                        
                        for k in range(len(driver1_positions)):
                            if driver1_positions[k] < driver2_positions[k]:
                                wins += 1
                            elif driver1_positions[k] > driver2_positions[k]:
                                losses += 1
                        
                        emoji1 = team_emoji_ids.get(team1)
                        emoji2 = team_emoji_ids.get(team2)
                        if emoji1 and emoji2:
                            team_emojis.append(f"       `{wins}`  {(str)(self.bot.get_emoji(emoji1))}   `{losses}`  ")
                            driver_name1.append(f"`{driver1}`")
                            driver_name2.append(f"`{driver2}`")
                        else:
                            driver_name.append(f"{driver1} vs {driver2} ({team1}): {wins}-{losses}")
                                        
            driver_name1 = '\n'.join(driver_name1)
            driver_name2 = '\n'.join(driver_name2)
            team_emojis = '\n'.join(team_emojis)
                
            message_embed.add_field(name="Driver", value=driver_name1,inline=True)
            message_embed.add_field(name="Team", value=team_emojis,inline=True)
            message_embed.add_field(name="Driver", value=driver_name2,inline=True)

    except Exception as e:
        print(f"Error: {e}")
    return message_embed

class Head2Head(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        
    @commands.Cog.listener()
    async def on_ready(self):
        print('Head2Head cog loaded')
        
    @app_commands.command(name='h2h', description='See head to head stats of specific drivers or teammate pairings. May take some time to load.')
    @app_commands.describe(event='Choose between Qualifying or Race')
    @app_commands.choices(event=[app_commands.Choice(name="Qualifying", value="Qualifying"), app_commands.Choice(name="Race", value="Race"),])
    async def head2head(self, interaction: discord.Interaction, driver1_code: typing.Optional[str], driver2_code: typing.Optional[str], event: app_commands.Choice[str]):
        await interaction.response.defer()
        loop = asyncio.get_running_loop()
        try:
            if driver2_code is None:
                if driver1_code is None:
                    h2h_embed = await loop.run_in_executor(None, head_to_head, self, 'null', 'null', event)
                else:
                    h2h_embed = await loop.run_in_executor(None, head_to_head, self, driver1_code, 'null', event)
            elif driver1_code is None:
                if driver2_code is not None:
                    h2h_embed = await loop.run_in_executor(None, head_to_head, self, 'null', driver2_code, event)
            else:   
                h2h_embed = await loop.run_in_executor(None, head_to_head, self, driver1_code, driver2_code, event)
        except Exception as e:
            h2h_embed.set_image(url='https://media.tenor.com/lxJgp-a8MrgAAAAd/laeppa-vika-half-life-alyx.gif')
            h2h_embed.description = f"Error Occured :( {e}"  
            print({e})
            
        try:
            await interaction.followup.send(embed=h2h_embed)
        except Exception as e:
            h2h_embed.set_image(url='https://media.tenor.com/lxJgp-a8MrgAAAAd/laeppa-vika-half-life-alyx.gif')
            h2h_embed.description = f"Error Occured :( {e}"            
            await interaction.followup.send(embed=h2h_embed)
        loop.close()

async def setup(bot):
    await bot.add_cog(Head2Head(bot))