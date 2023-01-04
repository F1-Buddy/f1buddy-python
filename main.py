import fastf1
import discord
import pandas as pd
from discord import app_commands
from fastf1 import plotting
# from matplotlib import pyplot as plt
from geopy.geocoders import Nominatim
from timezonefinder import TimezoneFinder

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


def test_next():
    # now = pd.Timestamp.now()
    # message_embed = discord.Embed(title="Race Schedule", description="")
    schedule = fastf1.get_event_schedule(2022, include_testing=False)

    next_event = 0
    test_time = pd.Timestamp(year=2022, month=9, day=3)
    out_string = ""

    
    for i in range(len(schedule)):
        if schedule.iloc[i].values[4] < test_time:
            next_event = i+1
    try:
        
       
        # TIME IS IN LOCAL NOT UTC
        date_object = schedule.iloc[next_event].values[16]
        # print('race start = ',date_object, ' local time')
        # session = fastf1.get_session(date_object.year,schedule.iloc[next_event].values[0],'R')
        g = Nominatim(user_agent='f1pythonbottesting')
        location = schedule.iloc[next_event].values[2]
        coords = g.geocode(location)
        # print(coords)
        tf = TimezoneFinder()
        tz = tf.timezone_at(lng=coords.longitude, lat=coords.latitude)
        date_object = date_object.tz_localize(tz).tz_convert('America/New_York')

        date = str(schedule.iloc[next_event].values[4].month) + "/"+ str(schedule.iloc[next_event].values[4].day)+"/"+ str(schedule.iloc[next_event].values[4].year)
        time = str(date_object)[str(date_object).index(":")-2:]
        time = time[:time.index("-")]
        # print(date_object)
        # print(date_object.tz_convert('America/New_York'))
        # print(tz)
        # session.load()
        # print(session.date)
        # print(date_object)
        # print('country = ',schedule.iloc[next_event].values[1])
        # print('location = ',schedule.iloc[next_event].values[2])

        out_string = ''.join([
            'Next event is the \n',
            str(schedule.iloc[next_event].values[3]),
            '\non **',
            date,
            '**\nat **',
            time,
            " EST** "
        ])
    except IndexError:
        out_string = ('It is currently off season! :crying_cat_face:')
    print(out_string)

test_next()

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
        # TIME IS IN LOCAL NOT UTC
        date_object = schedule.iloc[next_event].values[16]
        # print('race start = ',date_object, ' local time')
        # session = fastf1.get_session(date_object.year,schedule.iloc[next_event].values[0],'R')
        g = Nominatim(user_agent='f1pythonbottesting')
        location = schedule.iloc[next_event].values[2]
        #   get lat and long of the race location
        coords = g.geocode(location)
        # print(coords)
        #   find timezone using those coordinates
        tf = TimezoneFinder()
        tz = tf.timezone_at(lng=coords.longitude, lat=coords.latitude)
        date_object = date_object.tz_localize(tz).tz_convert('America/New_York')

        date = str(schedule.iloc[next_event].values[4].month) + "/"+ str(schedule.iloc[next_event].values[4].day)+"/"+ str(schedule.iloc[next_event].values[4].year)
        time = str(date_object)[str(date_object).index(":")-2:]
        time = time[:time.index("-")]
        # print(date_object)
        # print(date_object.tz_convert('America/New_York'))
        # print(tz)
        # session.load()
        # print(session.date)
        # print(date_object)
        # print('country = ',schedule.iloc[next_event].values[1])
        # print('location = ',schedule.iloc[next_event].values[2])

        out_string = ''.join([
            'Next event is the \n',
            str(schedule.iloc[next_event].values[3]),
            '\non **',
            date,
            '**\nat **',
            time,
            " EST** "
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
