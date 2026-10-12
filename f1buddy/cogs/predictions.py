from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands

from .. import util
from ..data import params
from ..data import predictions as game
from ..errors import UserError
from ..render import embeds
from . import common

MEDALS = ["🥇", "🥈", "🥉"]


def require_guild(interaction) -> int:
    if interaction.guild_id is None:
        raise UserError("Predictions are per server. Use this in a server.")
    return interaction.guild_id


def lock_text(event, part, now) -> str:
    lock = game.lock_time(event, part)
    return "locked" if lock <= now else f"locks {util.ts(lock, 'R')}"


def podium_text(row) -> str:
    return " · ".join(f"{m} {row[k]}" for m, k in zip(MEDALS, ("p1", "p2", "p3"))) if row and row["p1"] else "not set"


def my_prediction(event, row) -> discord.Embed:
    now = util.now()
    return embeds.make(f"Your prediction — {event.name}", "\n".join([
        f"**Pole:** {row['pole'] if row and row['pole'] else 'not set'} ({lock_text(event, 'pole', now)})",
        f"**Podium:** {podium_text(row)} ({lock_text(event, 'podium', now)})"]))


def predictions_embed(event, rows, viewer_id, result, now) -> tuple[discord.Embed, bool]:
    """(embed, must it be ephemeral?). Each part of a prediction is hidden from others until it locks."""
    pole_open = game.lock_time(event, "pole") > now
    podium_open = game.lock_time(event, "podium") > now
    lines = []
    if result:
        lines += [f"**Pole:** {result['pole']} · **Podium:** {' · '.join(result['podium'])}", ""]
    shown = 0
    for row in rows:
        mine = row["user_id"] == viewer_id
        pole = row["pole"] if (mine or not pole_open) and row["pole"] else None
        podium = podium_text(row) if (mine or not podium_open) and row["p1"] else None
        if not pole and not podium:
            continue
        if shown == 25:
            lines.append(f"…and {sum(1 for r in rows) - shown} more")
            break
        shown += 1
        score = f" — **{row['points']} pts**" if row["points"] is not None else ""
        lines.append(f"<@{row['user_id']}>: pole {pole or '–'} · podium {podium or '–'}{score}")
    if pole_open or podium_open:
        hidden = sum(1 for r in rows if r["p1"]) if not pole_open else len(rows)
        what = "a podium" if not pole_open else "a prediction"
        lines.append(f"\n{hidden} member(s) have entered {what}. "
                     f"Pole {lock_text(event, 'pole', now)}; podium {lock_text(event, 'podium', now)}.")
    if not rows:
        lines = ["No predictions yet. Use `/predict pole` and `/predict podium`."]
    return embeds.make(f"Predictions — {event.name}", "\n".join(lines)), pole_open or podium_open


def leaderboard_embed(year, guild_name, board, viewer_id) -> discord.Embed:
    if not board:
        return embeds.make(f"{year} Predictions Leaderboard — {guild_name}",
                           "No predictions have been scored yet this season.")
    def line(entry):
        rank, user_id, points, races, _ = entry
        return f"**{rank}.** <@{user_id}> — {points} pts ({races} race{'s' if races != 1 else ''})"
    lines = [line(e) for e in board[:10]]
    mine = next((e for e in board[10:] if e[1] == viewer_id), None)
    if mine:
        lines += ["…", line(mine)]
    return embeds.make(f"{year} Predictions Leaderboard — {guild_name}", "\n".join(lines))


def results_embed(event, result, round_rows, board) -> discord.Embed:
    """Posted to the weekend channel once a race has been scored."""
    top_round = [f"<@{r['user_id']}> — {r['points']} pts" for r in round_rows[:5]]
    top_season = [f"**{rank}.** <@{uid}> — {pts} pts" for rank, uid, pts, _, _ in board[:5]]
    embed = embeds.make(f"Prediction results — {event.name}",
                        f"**Pole:** {result['pole']}\n**Podium:** {' · '.join(result['podium'])}")
    embed.add_field(name="This race", value="\n".join(top_round) or "–", inline=True)
    embed.add_field(name="Season", value="\n".join(top_season) or "–", inline=True)
    return embed


class Predictions(commands.Cog):
    category = "Predictions"

    predict = app_commands.Group(name="predict", description="Predict pole and the podium for the next race")

    @predict.command(name="pole", description="Predict the pole-sitter; locks when qualifying starts")
    @app_commands.describe(driver="Driver you think will take pole")
    @app_commands.autocomplete(driver=common.driver_autocomplete)
    async def pole(self, interaction: discord.Interaction, driver: str):
        guild_id = require_guild(interaction)
        event, row = await game.save_pole(guild_id, interaction.user.id, driver)
        await interaction.response.send_message(embed=my_prediction(event, row), ephemeral=True)

    @predict.command(name="podium", description="Predict the top three; locks when the race starts")
    @app_commands.describe(p1="Winner", p2="Second place", p3="Third place")
    @app_commands.autocomplete(p1=common.driver_autocomplete, p2=common.driver_autocomplete,
                               p3=common.driver_autocomplete)
    async def podium(self, interaction: discord.Interaction, p1: str, p2: str, p3: str):
        guild_id = require_guild(interaction)
        event, row = await game.save_podium(guild_id, interaction.user.id, p1, p2, p3)
        await interaction.response.send_message(embed=my_prediction(event, row), ephemeral=True)

    @app_commands.command(name="predictions", description="See predictions for a race, and the scores once it's run")
    @app_commands.describe(round="Round name or number; defaults to the current race weekend",
                           user="Show one member's prediction")
    @app_commands.autocomplete(round=common.round_autocomplete)
    async def predictions(self, interaction: discord.Interaction, round: Optional[str] = None,
                          user: Optional[discord.Member] = None):
        guild_id = require_guild(interaction)
        now = util.now()
        if round:
            event = params.find_round(await params.season(now.year), round)
            if event is None or not (event.race and event.qualifying):
                raise UserError(f'Round "{round}" not found for {now.year}.')
        else:
            event = await game.current_event(now)
        rows = await game.for_event(guild_id, event)
        if user is not None:
            rows = [r for r in rows if r["user_id"] == user.id]
        embed, private = predictions_embed(event, rows, interaction.user.id, await game.actual(event), now)
        await interaction.response.send_message(embed=embed, ephemeral=private)

    @app_commands.command(name="leaderboard", description="Season predictions leaderboard for this server")
    @app_commands.describe(year="Season; defaults to the current one")
    async def leaderboard(self, interaction: discord.Interaction, year: Optional[int] = None):
        guild_id = require_guild(interaction)
        year = year or util.now().year
        board = await game.leaderboard(guild_id, year)
        await interaction.response.send_message(
            embed=leaderboard_embed(year, interaction.guild.name, board, interaction.user.id))

    @app_commands.command(name="predictions-rescore",
                          description="Recompute a race's prediction scores from the current official result")
    @app_commands.describe(round="Round name or number to rescore")
    @app_commands.autocomplete(round=common.round_autocomplete)
    @app_commands.checks.has_permissions(manage_guild=True)
    @app_commands.default_permissions(manage_guild=True)
    async def rescore(self, interaction: discord.Interaction, round: str):
        guild_id = require_guild(interaction)
        await interaction.response.defer(ephemeral=True)
        year = util.now().year
        event = await params.resolve_event(year, round)
        changed = await game.score_round(event, *await game.official_result(event))
        await interaction.followup.send(
            f"Rescored {event.name}: {changed.get(guild_id, 0)} score(s) changed in this server.", ephemeral=True)


async def setup(bot):
    await bot.add_cog(Predictions())
