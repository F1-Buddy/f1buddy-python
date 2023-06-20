# basic help command
import discord
from discord import app_commands
from discord.ext import commands
from lib.colors import colors

class Help(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        print('Help cog loaded')

    @app_commands.command(name='help', description='get help')
    async def help(self, interaction: discord.Interaction):
        # defer reply for later
        await interaction.response.defer()
        # setup embed
        message_embed = discord.Embed(title="f1buddy Help", description="If you are having any issues or want to provide feedback, please open a new issue on [GitHub](https://github.com/F1-Buddy/f1buddy-python/issues)\n\nTo see all commands and usage, type '/' and click on f1buddy as shown in the attached image\n")
        message_embed.colour = colors.default
        message_embed.set_thumbnail(
        url='https://cdn.discordapp.com/attachments/884602392249770087/1059464532239581204/f1python128.png')

        file = discord.File("cogs/plots/help/help.png", filename="help.png")


        # send embed
        message_embed.set_image(url='attachment://help.png')
        await interaction.followup.send(embed=message_embed,file=file)


async def setup(bot):
    await bot.add_cog(Help(bot))
