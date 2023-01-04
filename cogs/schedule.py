import discord
from discord import app_commands
from discord.ext import commands

class Schedule(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # print('hi')
    @commands.Cog.listener()
    async def on_ready(self):
        print('schedule cog loaded')

    # @commands.command()
    # async def sync(self, ctx) -> None:
    #     fmt = await ctx.bot.tree.sync(guild=ctx.guild)
    #     await ctx.send(f'Synced {len(fmt)}')

    @app_commands.command(name='schedule', description='get race schedule')
    async def schedule(self, interaction: discord.Interaction, question: str):
        #######################################################################
        # Put schedule command here from other branch + improvements
        # Remove question field
        #######################################################################
        outstring = 'message received = ' + question
        # print(outstring)
        await interaction.response.send_message(outstring)


async def setup(bot):
    await bot.add_cog(Schedule(bot), guilds=[discord.Object(id=884602392249770084)])