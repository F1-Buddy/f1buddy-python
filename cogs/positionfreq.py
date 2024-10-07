import asyncio
import discord
import typing
import pandas as pd
from fastf1.ergast import Ergast
import fastf1
from discord import app_commands
from discord.ext import commands
from lib.emojiid import team_emoji_ids
from lib.colors import colors
import repeated.common as cm
import repeated.embed as em
import traceback

now = pd.Timestamp.now().tz_localize("America/New_York")

##########################
# THE NATURE OF THIS COMMAND IS SLOWWWWWW!!!!
# IT REQUIRES PROCESSING OF EVERY LAP DRIVEN BY EVERY DRIVER OVER EVERY RACE IN A SEASON
# I'm sure there are some ways to optimize but not worth looking into right now
##########################


def get_frequencies(year):
    year = cm.check_year(year)
    schedule = fastf1.get_event_schedule(year=year, include_testing=False)
    latest_event = cm.latest_completed_index(year)
    emoji_map = {}  # driver -> emoji, i hate it
    position_freq = {}
    for race_index in range(min(schedule.index), latest_event + 1):
        race_session = fastf1.get_session(
            year, schedule.loc[race_index, "RoundNumber"], "R"
        )
        race_session.load(laps=True, telemetry=False, weather=False, messages=False)
        for lap_index in range(0, len(race_session.laps)):
            lap = race_session.laps.iloc[lap_index]
            try:
                curr_position = int(lap["Position"])
            except ValueError:
                # print(lap)
                continue
            if lap["Driver"] not in emoji_map:
                if lap["Team"] not in team_emoji_ids:
                    print(f"Team {lap['Team']} not found in emoji map")
                emoji_map[lap["Driver"]] = team_emoji_ids.get(lap["Team"], "")
            if curr_position not in position_freq:
                position_freq[curr_position] = {}
            if lap["Driver"] not in position_freq[curr_position]:
                position_freq[curr_position][lap["Driver"]] = 1
            else:
                position_freq[curr_position][lap["Driver"]] += 1

    return position_freq, emoji_map


def print_frequencies(self, data, emoji_map):
    out = ""
    for i in range(min(data.keys()), max(data.keys()) + 1):
        out += f"P{i}\t- "
        for driver in data[i]:
            if data[i][driver] == max(data[i].values()):
                out += f"{self.bot.get_emoji(emoji_map[driver])}{driver}"
                # out += f"{emoji_map[driver]}{driver} "
        # {[driver for driver in data[i] if data[i][driver] == max(data[i].values())]}
        out += f"({max(data[i].values())} laps)\n"
    return out


def generate_posfreq_embed(self, year):
    position_freq, emoji_map = get_frequencies(year)
    out = print_frequencies(self, position_freq, emoji_map)
    return em.Embed(
        title=f"Position Frequency for {cm.check_year(year)}",
        description=out,
    )


class position_freqeuency(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        print("Position Frequency cog loaded")

    @app_commands.command(
        name="positionfreq",
        description="Find out who has been in each position the most",
    )
    @app_commands.describe(year="Year")
    async def position_frequency(
        self, interaction: discord.Interaction, year: typing.Optional[int]
    ):
        await interaction.response.defer()
        loop = asyncio.get_running_loop()
        # run query and build embed
        position_frequency_embed = await loop.run_in_executor(
            None, generate_posfreq_embed, self, year
        )
        # send embed
        await interaction.followup.send(embed=position_frequency_embed.embed)
        loop.close()


async def setup(bot):
    await bot.add_cog(
        position_freqeuency(bot)  # , guilds=[discord.Object(id=884602392249770084)]
    )
