import discord
# import requests
# import json
import fastf1
import typing
import pandas as pd
from discord import app_commands
from discord.ext import commands
from lib.emojiid import team_emoji_ids
from pytube import Search, YouTube
from lib.colors import colors
import os
now = pd.Timestamp.now()

fastf1.Cache.enable_cache('cache/')

class Results2(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
    @commands.Cog.listener()
    async def on_ready(self):
        print('Results V2 cog loaded')  
    @app_commands.command(name = 'results', description = 'Get results of a specific race')
    @app_commands.describe(year = "Year")
    @app_commands.describe(round = "Round name or number (Australia or 3)")
    
    async def Results2(self, interaction: discord.Interaction, year: typing.Optional[int], round: typing.Optional[str]):  
        await interaction.response.defer()
        message_embed = discord.Embed(title=f"Race Results", description="").set_thumbnail(url='https://cdn.discordapp.com/attachments/884602392249770087/1059464532239581204/f1python128.png')
        message_embed.colour = colors.default
        
        # check if args are valid
        if (year == None):
            year = now.year
        if (round == None):
            # get latest completed session by starting from the end and going back towards beginning of season
            year_sched = fastf1.get_event_schedule(year,include_testing=False)
            round = (year_sched.shape[0])
            # print(round)
            # print(year_sched.loc[round, "Session5Date"].tz_convert('America/New_York'))
            sessionTime = year_sched.loc[round, "Session5Date"].tz_convert('America/New_York')
            while (now.tz_localize('America/New_York') < sessionTime):
                round -= 1
                sessionTime = year_sched.loc[round, "Session5Date"].tz_convert('America/New_York')
            result_session = fastf1.get_session(year, round, 'Race')
            result_session.load()
        # round given as number
        try:
            round_number = int(round)
            if (now.tz_localize('America/New_York') < fastf1.get_event_schedule(year,include_testing=False).loc[round_number, "Session5Date"].tz_convert('America/New_York')):
                message_embed.title = "Race not found!"
                message_embed.description = "Round " + (str)(round_number) + " not found!"
                await interaction.followup.send(embed = message_embed)
                return
            result_session = fastf1.get_session(year, round_number, 'Race')
            # message_embed.description = "Round number given: " + (str)(round_number)
            # print("Round number given: " + (str)(round_number))
            
        # round given as name
        except Exception as e:
            result_session = fastf1.get_session(year, round, 'Race')
            # print(e)
            # print("Round name given: " + round)
            
            # easter egg
            # if ('anurag' in round):
            #     message_embed.set_image(url='https://avatars.githubusercontent.com/u/100985214?v=4')
            # message_embed.description = "Round name given: "+round

        # load session
        result_session.load()
        resultsTable = result_session.results

        # test print
        # print(resultsTable)
        # print('\n\n')
        # print(resultsTable.columns.tolist())
        
        # get driver names and team emojis 
        driver_names = ""
        position_string = ""
        points_string = ""
        # status_string = ""
        if (resultsTable.empty):
            message_embed.description = "Race not found!"
            await interaction.followup.send(embed = message_embed)
            return
        for i in (resultsTable.DriverNumber.values):
            try:
                # print(resultsTable.loc[i,'TeamName'])
                driver_names += ((str)(self.bot.get_emoji(team_emoji_ids[resultsTable.loc[i,'TeamName']]))) + " " + resultsTable.loc[i,'FullName'] + "\n"
            except:
                driver_names += resultsTable.loc[i,'FullName'] + "\n"
            temp = (str)(resultsTable.loc[i,'Position'])
            temp_position = temp[0:temp.index('.')]
            match temp_position:
                case '1':
                    temp_position = ':first_place:'
                case '2':
                    temp_position = ':second_place:'
                case '3':
                    temp_position = ':third_place:'
            position_string += temp_position + "\n"
            temp_points = (str)(resultsTable.loc[i,'Points'])
            if temp_points[temp_points.index('.'):] == '.0':
                temp_points = temp_points[:temp_points.index('.')]
            points_string += temp_points + "\n"
            # status_string += (str)(resultsTable.loc[i,'Status']) + "\n"

        # print(driver_names)
        raceName = result_session.event.EventName
        message_embed.title = f"{year} {raceName} Race Results"

        s = Search((str)(year) + " " + raceName + " Highlights")
        video_url = 'https://www.youtube.com/watch?v='
        t = (str)(s.results[0])
        video_url += (t[t.index('videoId=')+8:-1])
        thumbnail = YouTube(video_url).thumbnail_url

        message_embed.add_field(name = "Position", value = position_string,inline = True)
        message_embed.add_field(name = "Driver", value = driver_names,inline = True)
        message_embed.add_field(name = "Points", value = points_string,inline = True)
        message_embed.add_field(name = "Race Highlights", value = video_url,inline = False)
        message_embed.set_image(url=thumbnail)
        # message_embed.add_field(name = "Status", value = status_string, inline = True)               
        # send final embed
        # message_embed.description = ""
        await interaction.followup.send(embed = message_embed)

async def setup(bot):
    await bot.add_cog(Results2(bot) # , guilds=[discord.Object(id=884602392249770084)]
                      )