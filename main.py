import fastf1
import discord
import config
import os
import asyncio
from discord.ext import commands


fastf1.Cache.enable_cache('cache/')
# basic bot setup
########################################
# token = open('token.txt').readline()
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix='f1$', intents=intents)
########################################

# On Ready
@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')



@bot.event
async def load():
    for file in os.listdir('./cogs'):
        if file.endswith('.py'):
            await bot.load_extension(f'cogs.{file[:-3]}')


async def main():
    await load()

    ########################################
    # START BOT
    await bot.start(config.TOKEN)
    ########################################

asyncio.run(main())


########################################
#
#   FastF1 example Hamilton vs Magnussen lap times 2020 Turkish GP
#
########################################

# race = fastf1.get_session(2020, 'Turkish Grand Prix', 'R')
# race.load()

# mag = race.laps.pick_driver('MAG')
# ham = race.laps.pick_driver('HAM')

# fig, ax = plt.subplots()
# ax.plot(mag['LapNumber'], mag['LapTime'], color='white')
# ax.plot(ham['LapNumber'], ham['LapTime'], color='cyan')
# ax.set_title("MAG vs HAM")
# ax.set_xlabel("Lap Number")
# ax.set_ylabel("Lap Time")
# plt.show()
