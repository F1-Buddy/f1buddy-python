import fastf1
import discord
import pandas as pd
from discord import app_commands
from fastf1 import plotting
from matplotlib import pyplot as plt


fastf1.Cache.enable_cache('cache/')
plotting.setup_mpl()


# basic bot setup
########################################
token = open('token.txt').readline()
intents = discord.Intents.default()
intents.message_content = True

client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)
########################################


# Next command
@tree.command(name="schedule", description="Get race schedule")
async def schedule_command(interaction):
    message_embed= discord.Embed(title="Race Schedule", description="")
    schedule2022 = fastf1.get_event_schedule(2022, include_testing=False)
    next_event = 0
    now = pd.Timestamp.now()
    test_time = pd.Timestamp(year=2021,month=1,day=1)
    out_string = ""

    for i in range(len(schedule2022)):
        if schedule2022.iloc[i].values[4] < now:
            next_event = i+1
    try:
        out_string = '{} {}'.format('Next event is the ',schedule2022.iloc[next_event].values[3])
    except IndexError:
        out_string = ('It is currently off season! :crying_cat_face:')
        message_embed.set_image(url='https://media.tenor.com/kdIoxRG4W4QAAAAC/crying-crying-kid.gif')
    message_embed.description = out_string
    message_embed.set_thumbnail(url='https://github.com/F1-Buddy/f1buddy-python/blob/dev-rakib/botPics/f1python128.png')
    await interaction.response.send_message(embed=message_embed)


# On Ready
@client.event
async def on_ready():
    await tree.sync()  # guild=discord.Object(id=884602392249770084))
    print(f'Logged in as {client.user}')

client.run(token)


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
