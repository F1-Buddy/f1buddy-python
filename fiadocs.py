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
    # get latest document
    document = s.find(class_='document-row').find('a')['href']
    fileName = document[document.index('/sites/default/files/decision-document/')+len('/sites/default/files/decision-document/'):]
    # print(fileName)
    filePath = f'cogs/fiaDocs/{fileName}'
    images = []
    if not (os.path.exists(f'cogs/fiaDocs/{fileName}')):
        # print(f'new doc = {fileName}')
        # make the file and save the pdf
        os.makedirs(filePath)
        doc = requests.get('https://www.fia.com/' + document)
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
        # print('already got, skipping')
        return None, None, None
    return images, fileName[:-4], ('https://www.fia.com/' + document.replace(" ","%20"))
    
async def threadMain(bot):
    channel_id = 1212636200217878528
    channel = bot.get_channel(channel_id)
    while (True):
        try:
            images,docName, doc_url = await getLatest()
            if images:
                message = await channel.send(embed=em.Embed(title='Latest FIA Doc',description=f"[{docName}]({doc_url})").embed,files=images)
                await message.publish()
                # print(images)
            await asyncio.sleep(30)
        except Exception as e:
            traceback.print_exc()
        
async def createDocThread(bot):
    thread = threading.Thread(await threadMain(bot))
    thread.start()
    