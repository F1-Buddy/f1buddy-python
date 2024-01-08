import discord
from lib.colors import colors
import sys
 
# setting path
sys.path.append('..\lib')

class Embed:
    embed = discord.Embed(title=f"Default Embed", description="").set_thumbnail(url='https://cdn.discordapp.com/attachments/884602392249770087/1059464532239581204/f1python128.png')
    embed.colour = colors.default
    def __init__(self, title = None, description = None, colour = None, image_url = None,thumbnail_url = None,author = None):
        self.embed.title = title
        self.embed.description = description
        self.embed.set_author(name=author[0], icon_url=author[1])
        self.embed.colour = colour
        self.embed.set_image(url = image_url)
        self.embed.set_thumbnail(url=thumbnail_url)
