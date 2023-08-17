import asyncio
import datetime
import discord
import typing
import traceback
import pandas as pd
import fastf1
from discord import app_commands
import country_converter as coco
from lib.emojiid import nation_dictionary
from discord.ext import commands
from fastf1.ergast import Ergast
from lib.emojiid import tire_emoji_ids, tire_emoji_ids_2018, team_emoji_ids
from lib.colors import colors
fastf1.Cache.enable_cache('cache/')
now = pd.Timestamp.now()
nationality_dict = nation_dictionary()
current_year = datetime.date.today().year

def fastest_lap_info(self, round_num, year, driver_name, driver_laptime, tyre_age, grand_prix):
    session = fastf1.get_session(year, round_num, 'Race')
    session.load(laps=True,telemetry=False,weather=False,messages=False)
    fastest_lap = session.laps.pick_fastest()
    
    driver = fastest_lap.loc['Driver']
    team = fastest_lap.loc['Team']
    team = team_emoji_ids.get(team)
    lap_time = fastest_lap.loc['LapTime']
    lap_time = (datetime.datetime.min + lap_time).time().strftime('%M:%S.%f')[:-3]
    tyre_life = int(fastest_lap.loc['TyreLife'])
    compound = fastest_lap.loc['Compound']
    if year <= 2018:
        compound = tire_emoji_ids_2018.get(compound)
    else:
        compound = tire_emoji_ids.get(compound)
    race_name = f"{session.event.EventName}"
    race_name = race_name.replace(" Grand Prix", "")
    
    try:
        emoji = ":flag_" + \
            (coco.convert(names=nationality_dict[race_name][0], to='ISO2')).lower()+":"
    except Exception as e:
        print(e)
        
    try:
        driver_laptime.append(f"{lap_time}")
        tyre_age.append(f"{(str)(self.bot.get_emoji(compound))} {tyre_life}")
        try:
            grand_prix.append(f"{emoji}\u00A0\u00A0\u00A0\u00A0{(str)(self.bot.get_emoji(team))} {driver}")
        except Exception as e:
            grand_prix.append(f"{race_name} {(str)(self.bot.get_emoji(team))} {driver}")
            print(e)
    except Exception as e:
        print(e)
    return driver_name, driver_laptime, tyre_age, grand_prix
    
    
def get_fastest_lap(self, round, year):
    try:
        round = int(round)
    except ValueError:
        round = round
        
    driver_name, driver_laptime, tyre_age, grand_prix = [],[],[],[]
    year_sched = fastf1.get_event_schedule(year, include_testing=False)
    num_rounds = year_sched.shape[0]
    
    if round == 999: # round==999 when user input for round is none, get all fastest laps
        try: 
            for round_num in range(1, num_rounds + 1):
                try:
                    sessionTime = year_sched.loc[round_num, "Session4Date"].tz_convert('America/New_York') if year_sched.loc[round_num, "EventFormat"] == 'conventional' else year_sched.loc[round_num, "Session2Date"].tz_convert('America/New_York')
                except Exception as e:
                    traceback.print_exc()
                    print(f"Error: {e}")

                if now.tz_localize('America/New_York') < sessionTime:
                    break
                try:
                    driver_name, driver_laptime, tyre_age, grand_prix = fastest_lap_info(self, round_num, year, driver_name, driver_laptime, tyre_age, grand_prix)
                except Exception as e:
                    print(f"An error occurred in round {round_num}: {e}")
                    continue
        except Exception as e:
            fastest_lap_embed.set_image(url='https://media.tenor.com/lxJgp-a8MrgAAAAd/laeppa-vika-half-life-alyx.gif')
            fastest_lap_embed.description = f"Error Occured :( {e}"        
    else: # if round not none, get lap for that round
        try:
            driver_name, driver_laptime, tyre_age, grand_prix = fastest_lap_info(self, round, year,driver_name, driver_laptime, tyre_age, grand_prix)
        except Exception as e:
            fastest_lap_embed.set_image(url='https://media.tenor.com/lxJgp-a8MrgAAAAd/laeppa-vika-half-life-alyx.gif')
            fastest_lap_embed.description = f"An error occurred in round {round}: :( {e}"   
            print(f"An error occurred in round {round}: {e}")   
            
    driver_name, driver_laptime, tyre_age, grand_prix = '\n'.join(driver_name), '\n'.join(driver_laptime), '\n'.join(grand_prix), '\n'.join(tyre_age)
    fastest_lap_embed = discord.Embed(title=f"Fastest Lap {year}", description="").set_thumbnail(url='https://cdn.discordapp.com/attachments/884602392249770087/1059464532239581204/f1python128.png')
    fastest_lap_embed.set_author(name='f1buddy',icon_url='https://raw.githubusercontent.com/F1-Buddy/f1buddy-python/main/botPics/f1pythonpfp.png')
    fastest_lap_embed.colour = colors.default
    fastest_lap_embed.add_field(name="GP     Name", value=tyre_age,inline=True)     
    fastest_lap_embed.add_field(name="Laptime", value=driver_laptime,inline=True)
    fastest_lap_embed.add_field(name="Age", value=grand_prix,inline=True)
    if year <= 2018:
        fastest_lap_embed.set_footer(text=f"{year} tires used",icon_url="https://cdn.discordapp.com/attachments/884602392249770087/1059464532239581204/f1python128.png")
    return fastest_lap_embed
     
class fastest_lap(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
    @commands.Cog.listener()
    async def on_ready(self):
        print('Fastest lap cog loaded')
        
    @app_commands.command(name='fl', description='Get fastest lap')
    @app_commands.describe(round = 'Round name or number (Australia or 3)')
    @app_commands.describe(year = "Year (supports 2018 and after)")
    async def fastest_lap(self, interaction: discord.Interaction, round: typing.Optional[str], year: typing.Optional[int]):
        await interaction.response.defer()
        fastest_lap_embed = discord.Embed(title=f"Fastest Lap", description="").set_thumbnail(url='https://cdn.discordapp.com/attachments/884602392249770087/1059464532239581204/f1python128.png')
        fastest_lap_embed.set_author(name='f1buddy',icon_url='https://raw.githubusercontent.com/F1-Buddy/f1buddy-python/main/botPics/f1pythonpfp.png')
        fastest_lap_embed.colour = colors.default
        loop = asyncio.get_running_loop()
        if round is None:
            round = 999
        if year is None:
            year = 2023
        try:
            if year < 2018 or year > current_year:
                raise YearNotValidException(f"Year cannot be before 2018 or after {current_year}!")
            try:
                event_round = int(round)
            except ValueError:
                pass
            try:
                if event_round:
                    if event_round < 0 or (event_round > 30 and event_round != 999):
                        raise RoundNotValidException(f"Enter a valid round number.")
            except:
                pass
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