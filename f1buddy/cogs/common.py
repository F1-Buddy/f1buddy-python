"""Bits every cog shares: autocomplete callbacks and sending helpers."""
import io

import discord
from discord import app_commands

from ..data import params


def _choices(pairs):
    return [app_commands.Choice(name=name[:100], value=value) for name, value in pairs]


async def round_autocomplete(interaction: discord.Interaction, current: str):
    return _choices(await params.round_choices(getattr(interaction.namespace, "year", None), current))


async def driver_autocomplete(interaction: discord.Interaction, current: str):
    return _choices(await params.driver_choices(getattr(interaction.namespace, "year", None), current))


SESSION_CHOICES = [app_commands.Choice(name=s, value=s) for s in params.SESSION_CHOICES]


def png_file(png: bytes, filename: str) -> discord.File:
    return discord.File(io.BytesIO(png), filename=filename)


async def send_pages(send, embed: discord.Embed, pages: list[bytes], note: str | None = None):
    """Send an embed with page images, at most 10 attachments per message. Returns the first message."""
    first = None
    for start in range(0, max(len(pages), 1), 10):
        files = [png_file(p, f"page-{start + i + 1:03}.png") for i, p in enumerate(pages[start:start + 10])]
        kwargs = {"files": files} if files else {}
        if start == 0:
            kwargs["embed"] = embed
        message = await send(**kwargs)
        first = first or message
    if note:
        await send(content=note)
    return first
