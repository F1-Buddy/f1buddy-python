import fastf1
import discord
import config
import os
import asyncio
import pandas as pd
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
test_event = fastf1.get_event(2022,13)
test_2022_schedule = fastf1.get_event_schedule(2022, include_testing=False)

print(test_2022_schedule)

# for i in range(len(test_2022_schedule)):
#     print("\nevent time = ")
#     print(test_2022_schedule.iloc[i].values[4])
#     now = pd.Timestamp.now()
test_time = pd.Timestamp(year=2022, month=9, day=1)
#     print(test_time-test_2022_schedule.iloc[i].values[4])

index = 0
# range starts at 2 because I skip 0 and 1 since I ignore preseason testing sessions
for i in range(2,len(test_2022_schedule)):
    if test_2022_schedule.loc[i,"Session1Date"] < test_time:
        index = i+1
eventName = test_2022_schedule.loc[index,"EventName"]
print(eventName)
session_15_p1_time = test_2022_schedule.loc[index,"Session1Date"]
print(session_15_p1_time)
print(test_time)
print(session_15_p1_time-test_time)

# print(test_2022_schedule.loc[15,"Session2Date"])
# print(test_2022_schedule.loc[15,"Session3Date"])
# print(test_2022_schedule.loc[15,"Session4Date"])
# print(test_2022_schedule.loc[15,"Session5Date"])
    

# Round 1
# DTSTART;TZID=Europe/London:20220320T150000
# DTEND;TZID=Europe/London:20220320T170000
# SUMMARY:FORMULA 1 GULF AIR BAHRAIN GRAND PRIX 2022 - Race
# Output = 2022-03-20 18:00:00

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
    # await bot.start(config.TOKEN)
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
