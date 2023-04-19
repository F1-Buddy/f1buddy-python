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

fastf1.Cache.enable_cache('./cache/')

class Quali2(commands.Cog):

    def __init__(self, bot: commands.Bot):
        self.bot = bot
    @commands.Cog.listener()
    async def on_ready(self):
        print('Quali V2 cog loaded')  
    @app_commands.command(name = 'quali', description = 'Get quali results V2')
    @app_commands.describe(year = "year")
    @app_commands.describe(round = "round name or number")
    async def Quali2(self, interaction: discord.Interaction, year: typing.Optional[int], round: typing.Optional[str]):  
        await interaction.response.defer()
        message_embed = discord.Embed(title=f"Quali Results", description="").set_thumbnail(url='https://cdn.discordapp.com/attachments/884602392249770087/1059464532239581204/f1python128.png')
        message_embed.colour = discord.Colour.dark_red() 
        
        # check if args are valid
        if (year == None):
            year = now.year
        if (round == None):
            round = 1
        # round given as number
        try:
            round_number = int(round)
            result_session = fastf1.get_session(year, round_number, 'Qualifying')
            # message_embed.description = "Round number given: " + (str)(round_number)
            # print("Round number given: " + (str)(round_number))
            
        # round given as name
        except Exception as e:
            result_session = fastf1.get_session(year, round, 'Qualifying')
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
        print(resultsTable)
        # print('\n\n')
        # print(resultsTable.columns.tolist())
        
        # get driver names and team emojis 
        driver_names = ""
        position_string = ""
        time_string = ""
        # status_string = ""
        if (resultsTable.empty):
            message_embed.description = "Session not found!"
            await interaction.followup.send(embed = message_embed)
            return
        for i in (resultsTable.DriverNumber.values):
            try:
                # print(resultsTable.loc[i,'TeamName'])
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
            
            
            # status_string += (str)(resultsTable.loc[i,'Status']) + "\n"

        # print(driver_names)
        raceName = result_session.event.EventName
        message_embed.title = f"{year} {raceName} Qualifying Results"

        s = Search((str)(year) + " " + raceName + " Qualifying Highlights")
        video_url = 'https://www.youtube.com/watch?v='
        t = (str)(s.results[0])
        video_url += (t[t.index('videoId=')+8:-1])
        thumbnail = YouTube(video_url).thumbnail_url

        message_embed.add_field(name = "Position", value = position_string,inline = True)
        message_embed.add_field(name = "Driver", value = driver_names,inline = True)
        message_embed.add_field(name = "Time", value = time_string,inline = True)
        message_embed.add_field(name = "Quali Highlights", value = video_url,inline = False)
        message_embed.set_image(url=thumbnail)
        # message_embed.add_field(name = "Status", value = status_string, inline = True)               
        # send final embed
        # message_embed.description = ""
        await interaction.followup.send(embed = message_embed)

async def setup(bot):
    await bot.add_cog(Quali2(bot) # , guilds=[discord.Object(id=884602392249770084)]
                      )