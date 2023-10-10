import discord
# import lib.timezones as timezones
import pandas as pd
import requests
from bs4 import BeautifulSoup
from discord import app_commands
from discord.ext import commands
from lib.colors import colors

# function that takes a timedelta and returns a countdown string
def countdown(totalseconds):
    out_string = ""
    days = int(totalseconds // 86400)
    totalseconds %= 86400
    hours = int(totalseconds // 3600)
    totalseconds %= 3600
    minutes = int(totalseconds // 60)
    seconds = totalseconds % 60
    seconds = int(seconds // 1)
    out_string += f"{days} days, {hours} hours, {minutes} minutes, and {seconds} seconds until the race!"
    return out_string

def upcomingEvents(tag):
    if 'upcoming' in tag.get_text():
        return tag
def findRace(tag):
    if 'Race' in tag.get_text() and 'MotoGP™' in tag.get_text() and "Press Conference" not in tag.get_text():
        return tag

class ScheduleMGP(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        print('MotoGP Schedule cog loaded')

    @app_commands.command(name='schedulemotogp', description='get MotoGP race schedule')
    async def scheduleMGP(self, interaction: discord.Interaction):
        # defer response
        await interaction.response.defer()
        # timestamp for now to find next event
        now = pd.Timestamp.now()
        
        # get next race
        url = "https://www.motogp.com/en/calendar/"
        html = requests.get(url=url)
        soup = BeautifulSoup(html.content, 'html.parser')
        next_event = soup.find(upcomingEvents, class_='calendar-listing__event')
        race_title = next_event.find(class_='calendar-listing__title').find(string=True).get_text(strip=True)
        race_circuit = next_event.find(class_='calendar-listing__location-track-name').get_text(strip=True)
        next_event_link = "https://www.motogp.com"+next_event['href']+"/race-centre"


        # get next race data
        html = requests.get(url=next_event_link)
        soup = BeautifulSoup(html.content, 'html.parser')
        race = soup.find(findRace,class_="race-centre-schedule__schedule")
        race_start_time = pd.Timestamp(race['data-start-time']).tz_convert('America/New_York')
        lap_count = race.find(class_="race-centre-schedule__schedule-laps").get_text(strip=True)

        # setup strings for embed
        desc_string = f"{race_circuit}"
        info_string = f':checkered_flag: **Race Start Time**\n:arrows_counterclockwise: **Lap Count**'
        values_string = f'`{race_start_time.strftime("%I:%M%p on %Y/%m/%d")}`\n{lap_count}'
        
        
        # setup embed
        message_embed = discord.Embed(title=f"{race_title} Schedule", description="")
        message_embed.colour = colors.default
        message_embed.add_field(name="", value=info_string,inline=True)
        message_embed.add_field(name="", value=values_string,inline=True)
        message_embed.set_footer(text="Times are displayed in EST") 
        message_embed.set_author(name='f1buddy',icon_url='https://raw.githubusercontent.com/F1-Buddy/f1buddy-python/main/botPics/f1pythonpfp.png')
        message_embed.set_thumbnail(
            url='https://cdn.discordapp.com/attachments/884602392249770087/1059464532239581204/f1python128.png')
        message_embed.description = desc_string
        
        # send embed
        await interaction.followup.send(embed=message_embed)


async def setup(bot):
    await bot.add_cog(ScheduleMGP(bot))
