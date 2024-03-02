import traceback
import discord
import asyncio
import fastf1
import typing
import pandas as pd
from discord import app_commands
from discord.ext import commands
from lib.emojiid import team_emoji_ids
from pytube import Search, YouTube
import repeated.embed as em
import repeated.common as cm


fastf1.Cache.enable_cache('cache/')

def quali_results(self,year,round):
    try:
        now = pd.Timestamp.now().tz_localize('America/New_York')
    
        year_OoB = (year is None) or ((year <= 1957) or (year >= now.year))
        if not year_OoB:
            year = year
        else:
            year = now.year
            if (cm.latest_quali_completed_index(now.year) == 0):
                year -= 1
            
        if (round == None):
            latest_quali_index = cm.latest_quali_completed_index(year) - 1
            if (latest_quali_index == 0):
                latest_quali_index += 1
            result_session = fastf1.get_session(year, latest_quali_index, 'Qualifying')
            result_session.load(laps=False, telemetry=False, weather=False, messages=False)
        else:
            event_round = None
            try:
                event_round = int(round)
            except:
                event_round = round
            result_session = fastf1.get_session(year, event_round, 'Qualifying')
            # inputs were valid, but the Qualifying hasnt happened yet
            if (now - result_session.date.tz_localize('America/New_York')).total_seconds() < 0:
                return em.ErrorEmbed(title="Qualifying not found!", error_message="Round \"" + (str)(event_round) + "\" not found")
            
        result_session.load(laps=False, telemetry=False, weather=False, messages=False)
        resultsTable = result_session.results
        
        driver_names = ""
        position_string = ""
        time_string = ""
        # status_string = ""
        if (resultsTable.empty):
            return em.ErrorEmbed(title="Session data not found!")
        
        for i in (resultsTable.DriverNumber.values):
            try:
                driver_names += ((str)(self.bot.get_emoji(team_emoji_ids[resultsTable.loc[i,'TeamName']]))) + " " + resultsTable.loc[i,'FullName'] + "\n"
            except:
                driver_names += resultsTable.loc[i,'FullName'] + "\n"
            temp = (str)(resultsTable.loc[i,'Position'])
            position_string += temp[0:temp.index('.')] + "\n"
            
            # get best lap time from furthest session driver made it to (Q3? -> Q2? -> Q1)
            time = (str)(resultsTable.loc[i,'Q3'])
            q = 3
            if ('NaT' in time):
                time = (str)(resultsTable.loc[i,'Q2'])
                q = 2
                if ('NaT' in time):
                    time = (str)(resultsTable.loc[i,'Q1'])
                    q = 1
                
            # print(time)
            try:
                time = time[11:((str)(time)).index('.')+4]
            except:
                time = time[11:] + ".000"
            time = "Q" +(str)(q)+": " + time 
            time_string += time + "\n"

        # print(driver_names)
        raceName = result_session.event.EventName

        s = Search((str)(year) + " " + raceName + " Qualifying")
        video_url = 'https://www.youtube.com/watch?v='
        t = (str)(s.results[0])
        video_url += (t[t.index('videoId=')+8:-1])

        dc_embed = em.Embed(title=f"{year} {raceName} Qualifying Results", footer="*Highlights video link below may not be accurate")
        dc_embed.embed.add_field(name = "Position", value = position_string,inline = True)
        dc_embed.embed.add_field(name = "Driver", value = driver_names,inline = True)
        dc_embed.embed.add_field(name = "Time", value = time_string,inline = True)
        return dc_embed.embed, video_url
    except Exception as e:
        traceback.print_exc()
        return em.ErrorEmbed(error_message=f'{str(type(e))}: {str(e)}'), None
        
    

class Quali2(commands.Cog):

    def __init__(self, bot: commands.Bot):
        self.bot = bot
    @commands.Cog.listener()
    async def on_ready(self):
        print('Quali V2 cog loaded')  
    @app_commands.command(name = 'qualifying', description = 'Get results of a qualifying session or the latest by leaving all options blank')
    @app_commands.describe(year = "Year")
    @app_commands.describe(round = "Round name or number (Australia or 3)")
    async def Quali2(self, interaction: discord.Interaction, year: typing.Optional[int], round: typing.Optional[str]):  
        await interaction.response.defer()
        loop = asyncio.get_running_loop()
        # run results query and build embed
        results_embed,video_url = await loop.run_in_executor(None, quali_results, self, year, round)
        results_embed.set_author(name='f1buddy',icon_url='https://raw.githubusercontent.com/F1-Buddy/f1buddy-python/main/botPics/f1pythonpfp.png')
        # send embed
        await interaction.followup.send(embed = results_embed)
        if not (video_url == None):
            await interaction.followup.send(video_url)
        loop.close()

async def setup(bot):
    await bot.add_cog(Quali2(bot) # , guilds=[discord.Object(id=884602392249770084)]
                      )