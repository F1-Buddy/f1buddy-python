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

# Next Command


@tree.command(name="schedule", description="Get race schedule")
async def schedule_command(interaction):
    now = pd.Timestamp.now()
    message_embed = discord.Embed(title="Race Schedule", description="")
    #########################################
    #
    #   change this
    #
    schedule = fastf1.get_event_schedule(2022, include_testing=False)
    #
    #   to this:
    #
    #       schedule = fastf1.get_event_schedule(now.year, include_testing=False)
    #
    #   before 2023 season!
    #
    #########################################
    next_event = 0
    test_time = pd.Timestamp(year=2021, month=1, day=1)
    out_string = ""

    for i in range(len(schedule)):
        if schedule.iloc[i].values[4] < now:
            next_event = i+1
    try:

        date = str(schedule.iloc[next_event].values[4].month) + "/"+ str(schedule.iloc[next_event].values[4].day)+"/"+ str(schedule.iloc[next_event].values[4].year)
        time = str(schedule.iloc[next_event].values[4])[str(schedule.iloc[next_event].values[4]).index(":")-2:]
        print(time)
        out_string = ''.join([
            'Next event is the \n',
            str(schedule.iloc[next_event].values[3]),
            '\non **',
            date,
            '**\nat **',
            time,
            "**"
        ])
    except IndexError:
        out_string = ('It is currently off season! :crying_cat_face:')
        message_embed.set_image(
            url='https://media.tenor.com/kdIoxRG4W4QAAAAC/crying-crying-kid.gif')
    message_embed.description = out_string
    message_embed.set_thumbnail(
        url='https://cdn.discordapp.com/attachments/884602392249770087/1059464532239581204/f1python128.png')
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
