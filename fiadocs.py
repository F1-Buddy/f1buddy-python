import asyncio
import traceback
import requests
import os
import threading
import fitz
import discord
from bs4 import BeautifulSoup
import repeated.embed as em

# same as command, only when files already exists return None instead of local files
async def getLatest():
    url = 'https://www.fia.com/documents/championships/fia-formula-one-world-championship-14/season/season-2024-2043'
    html = requests.get(url=url)
    s = BeautifulSoup(html.content, 'html.parser')
    doc_urls = []
    doc_names = []
    doc_paths = []
    discord_embeds = []
    discord_files = []
    documents = s.find_all(class_='document-row')
    for document in documents:
        dn = document.find('a')['href']
        fileName = dn[dn.index('decision-document/')+len('decision-document/'):]
        filePath = f'cogs/fiaDocs/{fileName[:-4]}'
        if not os.path.exists(filePath):
            doc_names.append(fileName)
            doc_paths.append(filePath)
            doc_urls.append('https://www.fia.com' + document.find('a')['href'].replace(" ","%20"))
    for i in reversed(range(len(doc_names))):
        images = []
        doc = requests.get(doc_urls[i])
        pdf = open(f"cogs/fiaDocs/{doc_names[i]}", 'wb')
        pdf.write(doc.content)
        pdf.close()
        os.makedirs(doc_paths[i])
        # convert pdf to images
        doc = fitz.open(f"cogs/fiaDocs/{doc_names[i]}")
        page_num = 0
        try:
            while (True):
                page = doc.load_page(page_num)  # number of page
                pix = page.get_pixmap(matrix=(fitz.Matrix(300 / 72, 300 / 72)))
                output = f"{doc_paths[i]}/{page_num}.png"
                pix.save(output)
                images.append(discord.File(f"{doc_paths[i]}/{page_num}.png", filename=f"{page_num}.png"))
                page_num += 1
        except ValueError:
            pass
        doc.close()
        discord_files.append(images)
        discord_embeds.append(em.Embed(title='Latest FIA Doc',description=f"[{doc_names[i][:-4]}]({doc_urls[i]})").embed)
        # delete the pdf
        os.remove(f"cogs/fiaDocs/{doc_names[i]}")
        await asyncio.sleep(2)
    return discord_embeds,discord_files
    
async def threadMain(bot):
    channel_id = 1212636200217878528
    channel = bot.get_channel(channel_id)
    while (True):
        try:
            dc_embeds, dc_files = await getLatest()
            for i in range(len(dc_embeds)):
                message = await channel.send(embed=dc_embeds[i],files=dc_files[i])
                await message.publish()
            await asyncio.sleep(300)
        except Exception as e:
            traceback.print_exc()
        
async def createDocThread(bot):
    thread = threading.Thread(await threadMain(bot))
    thread.start()
    