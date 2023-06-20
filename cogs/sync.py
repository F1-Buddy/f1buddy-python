# sync all commands
import discord
from discord.ext import commands

class Sync(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        print('Sync command loaded')

    # sync command
    # move into main if possible
    @commands.command()
    async def sync(self, ctx) -> None:
        # check if user ids are me anurag or jubayer
        if (ctx.message.author.id == 235835251052642315) | (ctx.message.author.id == 308274708262944769) | (ctx.message.author.id == 403699636612890624):
            # update status
            activity=discord.Activity(type=discord.ActivityType.listening, name=f"V10s | {len(self.bot.guilds)} servers")
            await self.bot.change_presence(activity=activity)
            # sync commands
            fmt = await ctx.bot.tree.sync()
            commands = len(fmt)
            user = self.bot.get_user(ctx.message.author.id)
            # send message
            await ctx.send(f'{user} synced {commands} commands')
        # other user tries to sync
        else:
            user = self.bot.get_user(ctx.message.author.id)
            await ctx.send(f"{user} is not a bot admin! Can't sync :(")
            
async def setup(bot):
    await bot.add_cog(Sync(bot))