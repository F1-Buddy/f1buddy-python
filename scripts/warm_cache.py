"""Pre-load a season so the first users don't wait: fastest laps, circuit images, season results.

    python scripts/warm_cache.py [year]

Safe to stop and re-run; everything it fetches is cached under DATA_DIR.
"""
import asyncio
import logging
import os
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))

from f1buddy import ctx, util  # noqa: E402
from f1buddy.config import Config  # noqa: E402
from f1buddy.data import info, params, plots  # noqa: E402
from f1buddy.db import Database  # noqa: E402
from f1buddy.sources import fastf1_src, jolpica  # noqa: E402


async def main(year: int):
    data_dir = pathlib.Path(os.environ.get("DATA_DIR") or "./data")
    (data_dir / "plots").mkdir(parents=True, exist_ok=True)
    ctx.config = Config(token="", admin_ids=frozenset(), data_dir=data_dir)
    ctx.db = Database(data_dir / "f1buddy.db")
    fastf1_src.init(data_dir)

    events = await params.season(year)
    print(f"{year}: {len(events)} events")
    await jolpica.season_results(year)
    await jolpica.season_qualifying(year)
    for event in events:
        if await plots.circuit_image(event):
            print(f"  circuit image: {event.name}")
    if year >= 2018:
        for event in params.completed(events, "Race"):
            try:
                lap = await info.fastest_lap(event)
                print(f"  fastest lap: {event.name} — {lap['code']} {util.fmt_lap(lap['seconds'])}")
            except Exception as e:
                print(f"  fastest lap: {event.name} — unavailable ({e})")
    print("constructor titles:", len(await jolpica.constructor_titles()), "constructors")


if __name__ == "__main__":
    logging.basicConfig(level="WARNING")
    asyncio.run(main(int(sys.argv[1]) if len(sys.argv) > 1 else util.now().year))
