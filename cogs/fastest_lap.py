import asyncio
import datetime
import discord
import typing
import traceback
import pandas as pd
import fastf1
from discord import app_commands
import pycountry
from lib.emojiid import nation_dictionary
from discord.ext import commands
from lib.emojiid import tire_emoji_ids, tire_emoji_ids_2018, team_emoji_ids
# from lib.colors import colors
import repeated.embed as em
import repeated.common as cm
fastf1.Cache.enable_cache('cache/')
now = pd.Timestamp.now()
nationality_dict = nation_dictionary()
current_year = datetime.date.today().year

# this code is fucked
# actually the worst command atm

def fastest_lap_info(self, round_num, year, driver_name, driver_laptime, tyre_age, grand_prix, emoji_list):
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
        country_name = session.session_info['Meeting']['Country']['Name']
        country = pycountry.countries.search_fuzzy(country_name)[0]
        alpha_2 = country.alpha_2
        emoji = f":flag_{alpha_2.lower()}:"
    except Exception as e:
        traceback.print_exc()
        print(e)
        
    try:
        driver_laptime.append(f"{lap_time}")
        tyre_age.append(f"{(str)(self.bot.get_emoji(compound))} {tyre_life}")
        try:
            grand_prix.append(f"{emoji}\u00A0\u00A0\u00A0\u00A0{(str)(self.bot.get_emoji(team))} {driver}")
        except Exception as e:
            traceback.print_exc()
            grand_prix.append(f"{race_name} {(str)(self.bot.get_emoji(team))} {driver}")
            print(e)
    except Exception as e:
        traceback.print_exc()
        print(e)
    return driver_name, driver_laptime, tyre_age, grand_prix
    
    
def get_fastest_lap(self, round, year):
    if (round is not None and round > cm.latest_completed_index(year)):
        return [em.ErrorEmbed(error_message=f"Round {round} hasn't occured yet!",title='Bad Round')]  
    driver_name, driver_laptime, tyre_age, grand_prix, emoji_list = [],[],[],[],[]
    # year_sched = fastf1.get_event_schedule(year, include_testing=False)
    
    if round == None: 
        for round_num in range(1, cm.latest_completed_index(year) + 1):
            try:
                driver_name, driver_laptime, tyre_age, grand_prix = fastest_lap_info(self, round_num, year, driver_name, driver_laptime, tyre_age, grand_prix, emoji_list)
            except Exception as e:
                traceback.print_exc()
                print(f"An error occurred in round {round_num}: {e}")
                continue
    else: # if round not none, get lap for that round
        try:
            driver_name, driver_laptime, tyre_age, grand_prix = fastest_lap_info(self, round, year,driver_name, driver_laptime, tyre_age, grand_prix, emoji_list)
        except Exception as e:
            traceback.print_exc()
            return [em.ErrorEmbed(error_message=traceback.format_exc())]

    # print('testing')
    num_races = len(grand_prix)
    if (num_races > 10):
        range1 =range(0,num_races//2)
        range2 =range(num_races//2,num_races)
        dc_embed1 = em.Embed(title=f"Fastest Lap {year}")
        dc_embed1.embed.add_field(name="GP     Name", value='\n'.join([grand_prix[i] for i in range1]),inline=True)
        dc_embed1.embed.add_field(name="Laptime", value='\n'.join([driver_laptime[i] for i in range1]),inline=True)
        dc_embed1.embed.add_field(name="Age", value='\n'.join([tyre_age[i] for i in range1]),inline=True)
        
        dc_embed2 = em.Embed(title=f"Fastest Lap {year} Continued")
        dc_embed2.embed.add_field(name="GP     Name", value='\n'.join([grand_prix[i] for i in range2]),inline=True)
        dc_embed2.embed.add_field(name="Laptime", value='\n'.join([driver_laptime[i] for i in range2]),inline=True)
        dc_embed2.embed.add_field(name="Age", value='\n'.join([tyre_age[i] for i in range2]),inline=True)
    else:
        dc_embed1 = em.Embed(title=f"Fastest Lap {year}")
        dc_embed1.embed.add_field(name="GP     Name", value='\n'.join(grand_prix),inline=True)
        dc_embed1.embed.add_field(name="Laptime", value='\n'.join(driver_laptime),inline=True)
        dc_embed1.embed.add_field(name="Age", value='\n'.join(tyre_age),inline=True)
        dc_embed2 = None
    
    # fastest_lap_embed = discord.Embed(title=, description="").set_thumbnail(url='https://cdn.discordapp.com/attachments/884602392249770087/1059464532239581204/f1python128.png')
    # fastest_lap_embed.set_author(name='f1buddy',icon_url='https://raw.githubusercontent.com/F1-Buddy/f1buddy-python/main/botPics/f1pythonpfp.png')
    # fastest_lap_embed.colour = colors.default
    # fastest_lap_embed.add_field(name="GP     Name", value=tyre_age,inline=True)     
    # fastest_lap_embed.add_field(name="Laptime", value=driver_laptime,inline=True)
    # fastest_lap_embed.add_field(name="Age", value=grand_prix,inline=True)
    if year <= 2018:
        dc_embed1.embed.set_footer(text=f"{year} tires used",icon_url="https://cdn.discordapp.com/attachments/884602392249770087/1059464532239581204/f1python128.png")
    return [dc_embed1,dc_embed2]
     
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
        # fastest_lap_embed = discord.Embed(title=f"Fastest Lap", description="").set_thumbnail(url='https://cdn.discordapp.com/attachments/884602392249770087/1059464532239581204/f1python128.png')
        # fastest_lap_embed.set_author(name='f1buddy',icon_url='https://raw.githubusercontent.com/F1-Buddy/f1buddy-python/main/botPics/f1pythonpfp.png')
        # fastest_lap_embed.colour = colors.default
        loop = asyncio.get_running_loop()
        fastest_lap_embeds = None
        if (year is None):
            year = now.year
            if (cm.currently_offseason()[0]) or (cm.latest_completed_index(now.year) == 0):
                year -= 1
        
        try:
            if (year < 2018) or (year > current_year):
                raise YearNotValidException(f"Year cannot be before 2018 or after {current_year}!")
            fastest_lap_embeds = await loop.run_in_executor(None, get_fastest_lap, self, round, year)
            # print(fastest_lap_embeds)
        # except YearNotValidException as ynve:
        #     fastest_lap_embed.set_image(url='https://media.tenor.com/lxJgp-a8MrgAAAAd/laeppa-vika-half-life-alyx.gif')
        #     fastest_lap_embed.description = f"{ynve}" 
        # except RoundNotValidException as rnve:
        #     fastest_lap_embed.set_image(url='https://media.tenor.com/lxJgp-a8MrgAAAAd/laeppa-vika-half-life-alyx.gif')
        #     fastest_lap_embed.description = f"{rnve}"
        except Exception as e:
            traceback.print_exc()
            fastest_lap_embeds = [em.ErrorEmbed()]
        try:
            # fastest_lap_embeds.remove(None)
            await interaction.followup.send(embeds=[dcembed.embed for dcembed in fastest_lap_embeds if dcembed is not None])
            
        except Exception as e:
            traceback.print_exc()
            # fastest_lap_embed.set_image(url='https://media.tenor.com/lxJgp-a8MrgAAAAd/laeppa-vika-half-life-alyx.gif')
            # fastest_lap_embed.description = f"Error Occured :( {e}" 
            await interaction.followup.send(embeds=[dcembed.embed for dcembed in fastest_lap_embeds if dcembed is not None])
            print(e)
        loop.close()
        
class YearNotValidException(Exception):
    pass

class RoundNotValidException(Exception):
    pass

async def setup(bot):
    await bot.add_cog(fastest_lap(bot))