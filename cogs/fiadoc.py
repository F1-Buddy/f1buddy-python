import asyncio
import requests
import discord
import typing
from bs4 import BeautifulSoup
import pandas as pd
from discord import app_commands
from discord.ext import commands
from lib.colors import colors
import fitz
import os
import repeated.embed as em

now = pd.Timestamp.now()
        
# sets embed color and title
message_embed = discord.Embed(title=f"Latest FIA Document", description="").set_thumbnail(url='https://cdn.discordapp.com/attachments/884602392249770087/1059464532239581204/f1python128.png')
message_embed.set_author(name='f1buddy',icon_url='https://raw.githubusercontent.com/F1-Buddy/f1buddy-python/main/botPics/f1pythonpfp.png')
message_embed.colour = colors.default        

def get_fia_doc(doc = None):
    message_embed.title = f"FIA Document {doc}"

    if doc is None:
        doc = 0
        message_embed.title = f"Latest FIA Document"

    # get fia site
    url = 'https://www.fia.com/documents/championships/fia-formula-one-world-championship-14/season/season-2024-2043'
    html = requests.get(url=url)
    s = BeautifulSoup(html.content, 'html.parser')
    # get latest document
    results = s.find_all(class_='document-row') #.find_all('a')
    documents = []
    for result in results:
        documents.append(result.find('a')['href'])
    if doc > len(documents):
        raise IndexError("womp womp")
    # print(documents)
    doc_url = 'https://www.fia.com/' + documents[doc]
    # create a file path for it
    # fileName = results[results.index('/sites/default/files/decision-document/')+len('/sites/default/files/decision-document/'):]
    # print(documents[doc])
    fileName = documents[doc][documents[doc].index('/sites/default/files/decision-document/')+len('/sites/default/files/decision-document/'):]
    # print(fileName)
    message_embed.description = fileName[:-4]
    filePath = f"cogs/fiaDocs/{fileName[:-4]}"
    images = []    
    # check if document already exists
    if not os.path.exists(f"{filePath}"):
        # make the file and save the pdf
        os.makedirs(filePath)
        doc = requests.get(doc_url)
        pdf = open(f"{filePath}/{fileName}", 'wb')
        pdf.write(doc.content)
        pdf.close()
        # convert pdf to images
        doc = fitz.open(f"{filePath}/{fileName}")
        page_num = 0
        try:
            while (True):
                page = doc.load_page(page_num)  # number of page
                pix = page.get_pixmap(matrix=(fitz.Matrix(300 / 72, 300 / 72)))
                output = f"{filePath}/{page_num}.png"
                pix.save(output)
                images.append(discord.File(f"{filePath}/{page_num}.png", filename=f"{page_num}.png"))
                page_num += 1
        except ValueError:
            pass
        doc.close()
        # delete the pdf
        os.remove(f"{filePath}/{fileName}")
    else:
        for image in os.listdir(filePath):
            images.append(discord.File(f"{filePath}/{image}", filename=f"{image}"))
        # print("Already got this document")
    return images
        
class fia_doc(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
    @commands.Cog.listener()
    async def on_ready(self):
        print('FIA Docs cog loaded')
    @app_commands.command(name='fiadoc', description='Get latest FIA Document')
    @app_commands.describe(doc = "Go back X documents")
    # @app_commands.describe(year = "Standings year")
    
    async def driver_standings(self, interaction: discord.InteractionMessage, doc: typing.Optional[int]):
        await interaction.response.defer()
        loop = asyncio.get_running_loop()
        # run query and build embed
        try:
            fia_doc_images = await loop.run_in_executor(None, get_fia_doc, doc)
            await interaction.followup.send(embed = message_embed, files = fia_doc_images)
        except IndexError:
            await interaction.followup.send(embed = em.ErrorEmbed(title="Document doesn't exist!").embed)
        # send embed
        loop.close()

async def setup(bot):
    await bot.add_cog(fia_doc(bot))