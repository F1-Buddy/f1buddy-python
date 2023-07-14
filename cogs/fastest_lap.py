import asyncio
import datetime
import discord
import typing
import pandas as pd
import fastf1
from discord import app_commands
import country_converter as coco
from lib.emojiid import nation_dictionary
from discord.ext import commands
from fastf1.ergast import Ergast
from lib.emojiid import tire_emoji_ids, team_emoji_ids
from lib.colors import colors
now = pd.Timestamp.now()
nationality_dict = nation_dictionary()
current_year = datetime.date.today().year

def fastest_lap_info(self, round_num, year,driver_name, driver_laptime, race_lap, tyre_age, grand_prix):
    session = fastf1.get_session(year, round_num, 'Race')
    session.load()
    fastest_lap = session.laps.pick_fastest()
    driver = fastest_lap.loc['Driver']
    team = fastest_lap.loc['Team']
    team = team_emoji_ids.get(team)
    lap_time = fastest_lap.loc['LapTime']
    lap_time = (datetime.datetime.min + lap_time).time().strftime('%M:%S.%f')[:-3]
    lap_number = int(fastest_lap.loc['LapNumber'])
    tyre_life = int(fastest_lap.loc['TyreLife'])
    compound = fastest_lap.loc['Compound']
    compound = tire_emoji_ids.get(compound)
    race_name = f"{session.event.EventName}"
    race_name = race_name.replace(" Grand Prix", "")
    try:
        emoji = ":flag_" + \
            (coco.convert(names=nationality_dict[race_name][0], to='ISO2')).lower()+":"
    except Exception as e:
        print(e)
    # driver_name.append(f"{(str)(self.bot.get_emoji(team))} {driver}")
    driver_laptime.append(f"{lap_time}")
    race_lap.append(f"{(str)(self.bot.get_emoji(compound))} {tyre_life}")
    tyre_age.append(f"{tyre_life}")
    grand_prix.append(f"{emoji}\u00A0\u00A0\u00A0\u00A0{(str)(self.bot.get_emoji(team))} {driver}")
    return driver_name, driver_laptime, tyre_age, race_lap, grand_prix
    
    
def get_fastest_lap(self, round, year):
    print("just year")
    driver_name, driver_laptime, race_lap, tyre_age, grand_prix = [],[],[],[],[]
    year_sched = fastf1.get_event_schedule(year, include_testing=False)
    num_rounds = year_sched.shape[0]
    if round == 999:
        try: 
            print("h")
            print(num_rounds)
            for round_num in range(1, num_rounds + 1):
                print("ok")
                sessionTime = year_sched.loc[round_num, "Session4Date"].tz_convert('America/New_York') if year_sched.loc[round_num, "EventFormat"] == 'conventional' else year_sched.loc[round_num, "Session2Date"].tz_convert('America/New_York')
                print(sessionTime)
                print("time")
                if now.tz_localize('America/New_York') < sessionTime:
                    break
                try:
                    driver_name, driver_laptime, tyre_age, race_lap, grand_prix = fastest_lap_info(self, round_num, year, driver_name, driver_laptime, race_lap, tyre_age, grand_prix)
                    print("dome")
                except Exception as e:
                    print(f"An error occurred in round {round_num}: {e}")
                    continue
        except Exception as e:
            fastest_lap_embed.set_image(url='https://media.tenor.com/lxJgp-a8MrgAAAAd/laeppa-vika-half-life-alyx.gif')
            fastest_lap_embed.description = f"Error Occured :( {e}"        
    else:    
        try:
            driver_name, driver_laptime, tyre_age, race_lap, grand_prix = fastest_lap_info(self, round, year,driver_name, driver_laptime, race_lap, tyre_age, grand_prix)
        except Exception as e:
            fastest_lap_embed.set_image(url='https://media.tenor.com/lxJgp-a8MrgAAAAd/laeppa-vika-half-life-alyx.gif')
            fastest_lap_embed.description = f"An error occurred in round {round}: :( {e}"   
            print(f"An error occurred in round {round}: {e}")   
            
    driver_name, driver_laptime, grand_prix, tyre_age, race_lap = '\n'.join(driver_name), '\n'.join(driver_laptime), '\n'.join(grand_prix), '\n'.join(tyre_age), '\n'.join(race_lap)
    fastest_lap_embed = discord.Embed(title=f"Fastest Lap {year}", description="").set_thumbnail(url='https://cdn.discordapp.com/attachments/884602392249770087/1059464532239581204/f1python128.png')
    fastest_lap_embed.set_author(name='f1buddy',icon_url='https://raw.githubusercontent.com/F1-Buddy/f1buddy-python/main/botPics/f1pythonpfp.png')
    fastest_lap_embed.colour = colors.default
    fastest_lap_embed.add_field(name="GP     Name", value=grand_prix,inline=True)     
    # fastest_lap_embed.add_field(name="Name", value= driver_name,inline=True)
    fastest_lap_embed.add_field(name="Laptime", value=driver_laptime,inline=True)
    fastest_lap_embed.add_field(name="Age", value=race_lap,inline=True)
    # fastest_lap_embed.add_field(name="Lap", value=race_lap,inline=True)
    # fastest_lap_embed.add_field(name="Age", value=tyre_age,inline=True)
    return fastest_lap_embed
     
class fastest_lap(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
    @commands.Cog.listener()
    async def on_ready(self):
        print('Fastest lap cog loaded')
        
    @app_commands.command(name='fl', description='Get fastest lap')
    @app_commands.describe(round = "Round for fastest lap")
    @app_commands.describe(year = "Year (supports 2018 and after)")
    async def fastest_lap(self, interaction: discord.Interaction, round: typing.Optional[int], year: typing.Optional[int]):
        await interaction.response.defer()
        fastest_lap_embed = discord.Embed(title=f"Fastest Lap", description="").set_thumbnail(url='https://cdn.discordapp.com/attachments/884602392249770087/1059464532239581204/f1python128.png')
        fastest_lap_embed.set_author(name='f1buddy',icon_url='https://raw.githubusercontent.com/F1-Buddy/f1buddy-python/main/botPics/f1pythonpfp.png')
        fastest_lap_embed.colour = colors.default
        loop = asyncio.get_running_loop()
        if round is None:
            round = 999
            print(round)
        if year is None:
            year = 2023
        try:
            if year < 2018 or year > current_year:
                raise YearNotValidException(f"Year cannot be before 2018 or after {current_year}!") 
            if round < 0 or (round > 30 and round != 999):
                raise RoundNotValidException(f"Enter a valid round number.")
            
            print('a') 
            print(f"{round} + {year}")
            fastest_lap_embed = await loop.run_in_executor(None, get_fastest_lap, self, round, year)
        except YearNotValidException as ynve:
            fastest_lap_embed.set_image(url='https://media.tenor.com/lxJgp-a8MrgAAAAd/laeppa-vika-half-life-alyx.gif')
            fastest_lap_embed.description = f"{ynve}" 
        except RoundNotValidException as rnve:
            fastest_lap_embed.set_image(url='https://media.tenor.com/lxJgp-a8MrgAAAAd/laeppa-vika-half-life-alyx.gif')
            fastest_lap_embed.description = f"{rnve}"
        except Exception as e:
            fastest_lap_embed.set_image(url='https://media.tenor.com/lxJgp-a8MrgAAAAd/laeppa-vika-half-life-alyx.gif')
            fastest_lap_embed.description = f"Error Occured :( {e}"            
        try:
            await interaction.followup.send(embed=fastest_lap_embed)
        except Exception as e:
            fastest_lap_embed.set_image(url='https://media.tenor.com/lxJgp-a8MrgAAAAd/laeppa-vika-half-life-alyx.gif')
            fastest_lap_embed.description = f"Error Occured :( {e}" 
            await interaction.followup.send(embed=fastest_lap_embed)
            print(e)
        loop.close()
        
class YearNotValidException(Exception):
    pass

class RoundNotValidException(Exception):
    pass

async def setup(bot):
    await bot.add_cog(fastest_lap(bot))