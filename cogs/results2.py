import discord
import requests
import json
import fastf1
import typing
import pandas as pd
from discord import app_commands
from discord.ext import commands
from lib.emojiid import team_emoji_ids
from pytube import Search
now = pd.Timestamp.now()

class Results2(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
    @commands.Cog.listener()
    async def on_ready(self):
        print('Results2 cog loaded')  
    @app_commands.command(name = 'results2', description = 'Get race results V2')
    @app_commands.describe(year = "year")
    @app_commands.describe(round = "round name or number")
    
    async def Results2(self, interaction: discord.Interaction, year: typing.Optional[int], round: typing.Optional[str]):  
        await interaction.response.defer()
        message_embed = discord.Embed(title=f"Race Results 2", description="").set_thumbnail(url='https://cdn.discordapp.com/attachments/884602392249770087/1059464532239581204/f1python128.png')
        if (year == None):
            year = now.year
        if (round == None):
            round = 1
        try:
            round_number = int(round)
            message_embed.description = "Round number given: " + (str)(round_number)
            print("Round number given: " + (str)(round_number))
            result_session = fastf1.get_session(year, round_number, 'Race')
            
        except Exception as e:
            print(e)
            print("Round name given: " + round)
            result_session = fastf1.get_session(year, round, 'Race')
            # if ('anurag' in round):
            #     message_embed.set_image(url='https://avatars.githubusercontent.com/u/100985214?v=4')
            message_embed.description = "Round name given: "+round
        result_session.load()
        resultsTable = result_session.results
        print(resultsTable)
        print('\n\n')
        print(resultsTable.columns.tolist())
        # print(resultsTable.BroadcastName.values)
        driver_names = ""
        for i in (resultsTable.DriverNumber.values):
            driver_names += ((str)(self.bot.get_emoji(team_emoji_ids[resultsTable.loc[i,'TeamName']]))) + " " + resultsTable.loc[i,'BroadcastName'] + "\n"
        print(driver_names)
        message_embed.colour = discord.Colour.dark_red()                
        # send final embed
        # message_embed.description = ""
        await interaction.followup.send(embed = message_embed)

async def setup(bot):
    await bot.add_cog(Results2(bot) # , guilds=[discord.Object(id=884602392249770084)]
                      )