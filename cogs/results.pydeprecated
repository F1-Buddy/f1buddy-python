import discord
import requests
import json
import fastf1
import typing
import pandas as pd
from discord import app_commands
from discord.ext import commands
from lib.emojiid import team_emoji_ids
from pytube import Search, YouTube
now = pd.Timestamp.now()

fastf1.Cache.enable_cache('cache/')

# check if given year and round number are valid
def checkYear(year, round):
    # cast to int to stop TypeError
    try:
        year = (int)(year)
        round = (int)(round)
        
        if not(year == None) and not(1950 <= year and year <= now.year):
            return "bad year"
        elif not(round == None) and not(round >= 1) and not(round < 25):
            return "bad round number"
        else:
            # if (year == None and round == None):
            #     url =  "https://ergast.com/api/f1/current/results.json"
            #     return url
            if (year == None and round != None):
                url = f"https://ergast.com/api/f1/{now.year}/{round}/results.json"
                return url
            elif (year != None and round == None):
                url =  f"https://ergast.com/api/f1/{year}/{1}/results.json"
                return url
            else: 
                url =  f"https://ergast.com/api/f1/{year}/{round}/results.json"
                return url
    except:
        url =  "https://ergast.com/api/f1/current/results.json"
        return url

class Results(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
    @commands.Cog.listener()
    async def on_ready(self):
        print('Race results cog loaded')  
    @app_commands.command(name = 'results', description = 'Get race results')
    @app_commands.describe(year = "Race results")
    
    async def Results(self, interaction: discord.Interaction, year: typing.Optional[int], round: typing.Optional[int]):  
        await interaction.response.defer()
        message_embed = discord.Embed(title=f"Race Results", description="").set_thumbnail(url='https://cdn.discordapp.com/attachments/884602392249770087/1059464532239581204/f1python128.png')
        message_embed.colour = discord.Colour.dark_red()
        url = checkYear(year,round)
        # print(url)
        description_string = ''
        if ('bad' in url):
            description_string = "Please try again with a different " + url[url.index('bad')+3:]
        else:
            driver_points, driver_position, driver_names = [], [], []
            try:
                results = requests.get(url)
                response = json.loads(results.content)
            except json.JSONDecodeError:
                if (year == None) or (1950 >= year and year >= now.year):
                    url = f"https://ergast.com/api/f1/current/results.json"
                    results = requests.get(url)
                    round = 1
                    response = json.loads(results.content)
                else:
                    url =  f"https://ergast.com/api/f1/{year}/{1}/results.json"
                    results = requests.get(url)
                    response = json.loads(results.content)
            # print(url)
            round_num =  len(response['MRData']['RaceTable']['Races'])-1
            amount_of_drivers = len(response['MRData']['RaceTable']['Races'][round_num]['Results'])
            if (amount_of_drivers == 0):
                    description_string = f"No available times for this round."     
            else:
                year = int(response['MRData']['RaceTable']['Races'][round_num]['season']) 
                raceName = (response['MRData']['RaceTable']['Races'][round_num]['raceName'])  
                message_embed.title = f"{year} {raceName} Race Results"


                # get youtube video
                s = Search((str)(year) + " " + raceName + " Highlights")
                video_url = 'https://www.youtube.com/watch?v='
                t = (str)(s.results[0])
                video_url += (t[t.index('videoId=')+8:-1])
                thumbnail = YouTube(video_url).thumbnail_url
                description_string = "Race Highlights:\n"+(video_url)

                for i in range(0, len(response['MRData']['RaceTable']['Races'][round_num]['Results'])):
                    race_results = (response['MRData']['RaceTable']['Races'][round_num]['Results'][i])
                    driver_data = (response['MRData']['RaceTable']['Races'][round_num]['Results'][i]['Driver'])
                    constructor_data = (response['MRData']['RaceTable']['Races'][round_num]['Results'][i]['Constructor'])
                    
                    try:
                        # print(amount_of_drivers)
                        if (amount_of_drivers <= 34):
                            print(((str)(self.bot.get_emoji(team_emoji_ids[constructor_data['name']]))) + ' ' + (driver_data['givenName']) + ' ' +  driver_data['familyName'])
                            driver_names.append(((str)(self.bot.get_emoji(team_emoji_ids[constructor_data['name']]))) + ' ' + (driver_data['givenName']) + ' ' +  driver_data['familyName'])
                            # print("got emoji")
                        else: 
                            driver_names.append((driver_data['givenName']) + ' ' +  driver_data['familyName'])
                            # print("didnt get emoji")
                    except:
                        driver_names.append((driver_data['givenName']) + ' ' + driver_data['familyName'])
                        
                    driver_position.append(race_results['position'])
                    driver_points.append(race_results['points'])
                    
                message_embed.add_field(name = "Position", value = '\n'.join(driver_position),inline = True)
                message_embed.add_field(name = "Driver", value = '\n'.join(driver_names),inline = True)
                message_embed.add_field(name = "Points", value = '\n'.join(driver_points),inline = True)
                message_embed.add_field(name = "Race Highlights", value = video_url, inline = False)
                message_embed.set_image(url=thumbnail)

        # send final embed
        # message_embed.description = description_string
        await interaction.followup.send(embed = message_embed)

async def setup(bot):
    await bot.add_cog(Results(bot) # , guilds=[discord.Object(id=884602392249770084)]
                      )