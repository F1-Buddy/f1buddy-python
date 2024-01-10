import discord
from lib.colors import colors

class Embed:
    embed = discord.Embed(title=f"Default Embed", description="").set_thumbnail(url='https://cdn.discordapp.com/attachments/884602392249770087/1059464532239581204/f1python128.png')
    embed.set_author(name='f1buddy',icon_url='https://raw.githubusercontent.com/F1-Buddy/f1buddy-python/main/botPics/f1pythonpfp.png')
    embed.colour = colors.default
    def __init__(self, title = None, description = None, colour = None, image_url = None,thumbnail_url = None,author = None, footer = None):
        self.embed.clear_fields()
        if not (title == None):
            self.embed.title = title
        if not (description == None):
            self.embed.description = description
        if  (not (author == None) and len(author) == 2):
            self.embed.set_author(name=author[0], icon_url=author[1])
        if not (colour == None):
            self.embed.colour = colour
        if not (image_url == None):
            self.embed.set_image(url = image_url)
        if not (thumbnail_url == None):
            self.embed.set_thumbnail(url=thumbnail_url)
        if not (footer == None):
            self.embed.set_footer(text=footer)
class ErrorEmbed(Embed):
    def __init__(self,title = None, error_message = None):
        gif_url = 'https://media.tenor.com/lxJgp-a8MrgAAAAd/laeppa-vika-half-life-alyx.gif'
        super().__init__(title=title,
                         description='Error Occured :(', 
                         image_url=gif_url,  
                         footer=error_message
                         )
class OffseasonEmbed(Embed):
    def __init__(self):
        gif_url = 'https://media.tenor.com/kdIoxRG4W4QAAAAC/crying-crying-kid.gif'
        super().__init__(title='Race Schedule', 
                         description='It is currently off season! :crying_cat_face:', 
                         image_url=gif_url
                         )