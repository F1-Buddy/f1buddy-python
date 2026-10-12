"""Run data + render functions against the real services. Usage: python scripts/smoke.py info|plots|..."""
import asyncio, sys, pathlib, traceback
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))
from f1buddy import ctx, config
from f1buddy.db import Database
from f1buddy.sources import fastf1_src

def boot():
    cfg = config.load({"DISCORD_TOKEN": "x", "ADMIN_USER_IDS": "1", "DATA_DIR": "./data"})
    cfg.data_dir.mkdir(exist_ok=True); (cfg.data_dir / "plots").mkdir(exist_ok=True)
    ctx.config = cfg; ctx.db = Database(cfg.data_dir / "f1buddy.db"); fastf1_src.init(cfg.data_dir)

def show(e):
    d = e.to_dict()
    print("  TITLE:", d.get("title"), "|", (d.get("description") or "")[:200].replace("\n", " / "))
    for f in d.get("fields", []):
        print("   ", f["name"], "=>", f["value"][:230].replace("\n", " | "))
    if d.get("footer"): print("   footer:", d["footer"]["text"])

async def step(name, coro):
    print("==", name)
    try:
        return await coro
    except Exception as e:
        print("  FAILED:", type(e).__name__, e); traceback.print_exc(limit=3)

async def info():
    from f1buddy.data import info as I
    from f1buddy.render import embeds as E
    v = await step("schedule", I.schedule());  v and show(E.schedule(v))
    v = await step("wdc", I.driver_standings(None)); v and show(E.wdc(v))
    v = await step("wcc 2007", I.constructor_standings(2007)); v and show(E.wcc(v))
    v = await step("results", I.race_results(None, None)); v and show(E.results(v))
    v = await step("results 1988 monaco", I.race_results(1988, "monaco")); v and show(E.results(v))
    v = await step("quali", I.qualifying_results(None, None)); v and show(E.results(v, "Qualifying"))
    v = await step("quali 2003 r1", I.qualifying_results(2003, "1")); v and show(E.results(v, "Qualifying"))
    v = await step("fl one", I.fastest_laps(2024, "5")); v and [show(e) for e in E.fastest_laps(*v)]
    v = await step("driver", I.driver_profile("hamilton")); v and (show(E.driver(v)), print("  photo", v.photo))
    v = await step("driver senna", I.driver_profile("Ayrton Senna")); v and show(E.driver(v))
    v = await step("constructors", I.constructors(None)); v and show(E.constructors(*v))

if __name__ == "__main__":
    boot()
    asyncio.run(globals()[sys.argv[1]]())
