import asyncio
import datetime
import typing
import discord
import fastf1
import unidecode
import pandas as pd
import country_converter as coco
# from cogs.avgpos import avg_pos
from lib import colors
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


def avg_pos(sessiontype):
    # get latest completed session by starting from the end of calendar and going back towards the beginning of the season
    year_sched = fastf1.get_event_schedule(current_year, include_testing=False)
    num_rounds = year_sched.shape[0]
    driver_positions, driver_teams = {}, [] # driver_pos keeps driver name and pos, driver_teams keeps order of driver positions by teamname

    for round_num in range(1, num_rounds + 1):
        sessionTime = year_sched.loc[round_num, "Session4Date"].tz_convert('America/New_York') if year_sched.loc[round_num, "EventFormat"] == 'conventional' else year_sched.loc[round_num, "Session2Date"].tz_convert('America/New_York')
        if now.tz_localize('America/New_York') < sessionTime:
            break
        
        try:
            result_session = fastf1.get_session(current_year, round_num, sessiontype)
            result_session.load()
            resultsTable = result_session.results
        except Exception as e:
            print(f"An error occurred in round {round_num}: {e}")
            continue

        for i in resultsTable.DriverNumber.values:
            try:
                team_name = resultsTable.loc[i, 'TeamName']
            except:
                pass
            driver_positions.setdefault(resultsTable.loc[i, 'FullName'], []).append(int(resultsTable.loc[i, 'Position']))
            driver_teams.append(team_name)  # add team name to the separate list
            
    return driver_positions, driver_teams

def head_to_head(driver1_code, driver2_code, sessiontype):
    ergast = Ergast()
    nationality_dict = nation_dictionary()
    driver_info = ergast.get_driver_info(season=current_year)
    driver_dictionary = {}
    for _, row in driver_info.iterrows():
        given_name = unidecode.unidecode(row['givenName'])
        family_name = unidecode.unidecode(row['familyName'])
        full_name = given_name + ' ' + family_name
        nationality = row['driverNationality']
        driver_dictionary[full_name] = nationality
    driver_positions, driver_teams = avg_pos(sessiontype)
    code_to_name = {code: name for name, code in driver_names.items()}  # Mapping of three-letter codes to full names
    wins, losses = 0, 0
    driver_name = []

    try:       
        if driver1_code and driver2_code:
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
                        if driver1 in driver_dictionary and driver2 in driver_dictionary:
                            nationality1 = driver_dictionary[driver1]
                            nationality2 = driver_dictionary[driver2]
                            emoji1 = ":flag_" + \
                                (coco.convert(
                                names=nationality_dict[nationality1][0], to='ISO2')).lower()+":"
                            emoji2 = ":flag_" + \
                                (coco.convert(
                                names=nationality_dict[nationality2][0], to='ISO2')).lower()+":"
                            driver_name.append(f"{emoji1} {driver1} vs {emoji2} {driver2}: {wins}-{losses}")
                            print(driver_name)
                        else:
                            print(f"{driver1} vs {driver2}: {wins}-{losses}")
                            driver_name.append(f"{driver1} vs {driver2}: {wins}-{losses}")
                    except Exception as e:
                        print(f"Error: {e}")
                else:
                    print(f"Insufficient data for the head-to-head comparison between {driver1} and {driver2}.")
            else:
                print("Invalid driver code.")
        
        elif driver1_code:
            driver1 = code_to_name.get(driver1_code)
            driver1_positions = driver_positions.get(driver1)
            
            if driver1_positions:
                for driver, positions in driver_positions.items():
                    if driver != driver1:
                        for i in range(len(driver1_positions)):
                            if driver1_positions[i] < positions[i]:
                                wins += 1
                            elif driver1_positions[i] > positions[i]:
                                losses += 1
                        try:
                            if driver1 in driver_dictionary and driver in driver_dictionary:
                                nationality1 = driver_dictionary[driver1]
                                nationality2 = driver_dictionary[driver]
                                emoji1 = ":flag_" + \
                                    (coco.convert(
                                    names=nationality_dict[nationality1][0], to='ISO2')).lower()+":"
                                emoji2 = ":flag_" + \
                                    (coco.convert(
                                    names=nationality_dict[nationality2][0], to='ISO2')).lower()+":"
                                driver_name.append(f"{emoji1} {driver1} vs {emoji2} {driver}: {wins}-{losses}")
                                print(driver_name)
                            else:
                                print(f"{driver1} vs {driver}: {wins}-{losses}")
                                driver_name.append(f"{driver1} vs {driver}: {wins}-{losses}")
                        except Exception as e:
                            print(f"Error: {e}")
                            wins, losses = 0, 0
            else:
                print("Invalid driver code.")
        elif driver1_code == '' and driver2_code =='':
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
                            
                            emoji_id1 = team_emoji_ids.get(team1)
                            emoji_id2 = team_emoji_ids.get(team2)
                            if emoji_id1 and emoji_id2:
                                driver_name.append(f"{emoji_id1} {driver1} vs {emoji_id2} {driver2} ({team1}): {wins}-{losses}")
                            else:
                                driver_name.append(f"{driver1} vs {driver2} ({team1}): {wins}-{losses}")
                            print(driver_name)
    except Exception as e:
        print(f"Error: {e}")
        
    message_embed = discord.Embed(title=f"H2H", description="").set_thumbnail(url='https://cdn.discordapp.com/attachments/884602392249770087/1059464532239581204/f1python128.png')
    message_embed.set_author(name='f1buddy',icon_url='https://raw.githubusercontent.com/F1-Buddy/f1buddy-python/main/botPics/f1pythonpfp.png')
    message_embed.colour = colors.default
    message_embed.set_thumbnail(url='https://cdn.discordapp.com/attachments/884602392249770087/1059464532239581204/f1python128.png')    
    message_embed.add_field(name="H2H", value=driver_name,inline=True)
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
        h2h_embed = await loop.run_in_executor(None, head_to_head, driver1_code, driver2_code, event)
        try:
            await interaction.followup.send(embed=h2h_embed)
        except Exception as e:
            h2h_embed.set_image(url='https://media.tenor.com/lxJgp-a8MrgAAAAd/laeppa-vika-half-life-alyx.gif')
            h2h_embed.description = f"Error Occured :( {e}"            
            await interaction.followup.send(embed=h2h_embed)
        loop.close()

async def setup(bot):
    await bot.add_cog(Head2Head(bot))