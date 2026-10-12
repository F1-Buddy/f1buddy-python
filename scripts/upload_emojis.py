"""Upload every image in f1buddy/assets/emojis/ as an application emoji, named after the file.

    DISCORD_TOKEN=... python scripts/upload_emojis.py

Team emojis are named after the team id (red_bull.png, ferrari.png, mclaren.png, ...).
Tyre emojis are tyre_soft.png, tyre_medium.png, tyre_hard.png, tyre_intermediate.png, tyre_wet.png,
with a _2018 suffix for the 2018 compounds (tyre_hypersoft_2018.png, ...).
Emojis that already exist are skipped, so this is safe to re-run after adding files.
"""
import asyncio
import os
import pathlib
import sys

import discord

EMOJI_DIR = pathlib.Path(__file__).parent.parent / "f1buddy" / "assets" / "emojis"


async def main():
    token = os.environ.get("DISCORD_TOKEN")
    if not token:
        sys.exit("Set DISCORD_TOKEN first.")
    client = discord.Client(intents=discord.Intents.none())
    await client.login(token)
    try:
        existing = {e.name for e in await client.fetch_application_emojis()}
        for path in sorted(EMOJI_DIR.glob("*")):
            if path.suffix.lower() not in (".png", ".jpg", ".jpeg", ".gif", ".webp"):
                continue
            if path.stem in existing:
                print(f"exists   {path.stem}")
                continue
            await client.create_application_emoji(name=path.stem, image=path.read_bytes())
            print(f"uploaded {path.stem}")
    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())
