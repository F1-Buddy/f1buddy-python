import fastf1
import discord
import config
import os
import asyncio
from discord.ext import commands


# basic bot setup
########################################
# token = open('token.txt').readline()
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='f1$',intents=intents,application_id='1059405703116242995')


# tree = app_commands.CommandTree(client)
########################################


########################################
# testing schedule
########################################

# https://theoehrly.github.io/Fast-F1/events.html#fastf1.events.Event
# https://theoehrly.github.io/Fast-F1/events.html#fastf1.events.EventSchedule
eventT = fastf1.get_event(2022,13)
# Round 13
# DTSTART;TZID=Europe/London:20220731T140000
# DTEND;TZID=Europe/London:20220731T160000
# SUMMARY:FORMULA 1 MAGYAR NAGYDÍJ 2022 - Race
# Output = 2022-07-31 15:00:00

# Round 14
# DTSTART;TZID=Europe/London:20220828T140000
# DTEND;TZID=Europe/London:20220828T160000
# SUMMARY:FORMULA 1 ROLEX BELGIAN GRAND PRIX 2022 - Race
# Output = 2022-08-28 15:00:00

# Round 18
# DTSTART;TZID=Europe/London:20221009T060000
# DTEND;TZID=Europe/London:20221009T080000
# SUMMARY:FORMULA 1 JAPANESE GRAND PRIX 2022 - Race
# Output = 2022-10-09 14:00:00

# for i in range(5):
    # print(eventT.get_session(i+1).date.tz_localize('UTC'))






# On Ready
@bot.event
async def on_ready():
    # await tree.sync()  # guild=discord.Object(id=884602392249770084))
    print(f'Logged in as {bot.user}')

@bot.event
async def load():
    for file in os.listdir('./cogs'):
        if file.endswith('.py'):
            await bot.load_extension(f'cogs.{file[:-3]}')

    # race = fastf1.get_session(2022, 10, 'R')
    # racename = '' + str(race.date.year)+' '+str(race.event.EventName)
    # print(racename)

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
