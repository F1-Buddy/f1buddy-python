import discord
from discord import app_commands
from discord.ext import commands

class Laptimes(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # print('hi')
    @commands.Cog.listener()
    async def on_ready(self):
        print('Laptimes cog loaded')

    @commands.command()
    async def sync(self, ctx) -> None:
        fmt = await ctx.bot.tree.sync(guild=ctx.guild)
        await ctx.send(f'Synced {len(fmt)}')

    @app_commands.command(name='laptimes', description='compare laptimes of two drivers in a race')
    @app_commands.describe(drivers='Drivers')
    @app_commands.choices(drivers=[
        discord.app_commands.Choice(name="HAM",value=1),
        discord.app_commands.Choice(name="RUS",value=2),
        discord.app_commands.Choice(name="VER",value=3),
        discord.app_commands.Choice(name="PER",value=4),
        discord.app_commands.Choice(name="LEC",value=5),
        discord.app_commands.Choice(name="SAI",value=6),
        discord.app_commands.Choice(name="ALO",value=7),
        discord.app_commands.Choice(name="OCO",value=8),
        discord.app_commands.Choice(name="GAS",value=9),
        discord.app_commands.Choice(name="TSU",value=10),
        discord.app_commands.Choice(name="BOT",value=11),
        discord.app_commands.Choice(name="ZHO",value=12),
        discord.app_commands.Choice(name="NOR",value=13),
        discord.app_commands.Choice(name="RIC",value=14),
        discord.app_commands.Choice(name="MAG",value=15),
        discord.app_commands.Choice(name="MSC",value=16),
        discord.app_commands.Choice(name="ALB",value=17),
        discord.app_commands.Choice(name="LAT",value=18),
        discord.app_commands.Choice(name="VET",value=19),
        discord.app_commands.Choice(name="STR",value=20)
    ])
    @app_commands.choices(drivers2=[
        discord.app_commands.Choice(name="HAM",value=1),
        discord.app_commands.Choice(name="RUS",value=2),
        discord.app_commands.Choice(name="VER",value=3),
        discord.app_commands.Choice(name="PER",value=4),
        discord.app_commands.Choice(name="LEC",value=5),
        discord.app_commands.Choice(name="SAI",value=6),
        discord.app_commands.Choice(name="ALO",value=7),
        discord.app_commands.Choice(name="OCO",value=8),
        discord.app_commands.Choice(name="GAS",value=9),
        discord.app_commands.Choice(name="TSU",value=10),
        discord.app_commands.Choice(name="BOT",value=11),
        discord.app_commands.Choice(name="ZHO",value=12),
        discord.app_commands.Choice(name="NOR",value=13),
        discord.app_commands.Choice(name="RIC",value=14),
        discord.app_commands.Choice(name="MAG",value=15),
        discord.app_commands.Choice(name="MSC",value=16),
        discord.app_commands.Choice(name="ALB",value=17),
        discord.app_commands.Choice(name="LAT",value=18),
        discord.app_commands.Choice(name="VET",value=19),
        discord.app_commands.Choice(name="STR",value=20)
    ])
    async def laptimes(self, interaction: discord.Interaction, drivers: discord.app_commands.Choice[int], drivers2: discord.app_commands.Choice[int], round: int):

        outstring = 'message received = ' + str(drivers.name) + ' ' + str(drivers2.name) + ' ' + str(round)
        # print(outstring)
        await interaction.response.send_message(outstring)


async def setup(bot):
    await bot.add_cog(Laptimes(bot), guilds=[discord.Object(id=884602392249770084)])