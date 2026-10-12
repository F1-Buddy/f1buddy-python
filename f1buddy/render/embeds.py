"""Result dataclasses -> discord.Embed. Pure functions; no fetching."""
import random

import discord

from .. import util

COLOUR = 0xE10600
EMOJIS: dict[str, str] = {}     # application emoji name -> "<:name:id>", filled at start-up
AVATAR_URL: str | None = None   # the bot's own avatar, set at start-up

OFFSEASON_GIFS = [
    "https://media.tenor.com/kdIoxRG4W4QAAAAC/crying-crying-kid.gif",
    "https://media1.tenor.com/m/Aopm1M7LJSUAAAAd/toto-smash-toto-wolff.gif",
    "https://media1.tenor.com/m/SM_22nlNWhkAAAAC/fernando-alonso-alonso.gif",
    "https://media1.tenor.com/m/9atYe_gKtbMAAAAd/sainz-sainz-jr.gif",
    "https://media1.tenor.com/m/YlbGgdszkpEAAAAC/george-russel-f1.gif",
]
MEDALS = {"1": "🥇", "2": "🥈", "3": "🥉"}


def make(title=None, description="", footer=None) -> discord.Embed:
    embed = discord.Embed(title=util.clamp(title, 256) if title else None,
                          description=util.clamp(description, 4096), colour=COLOUR)
    embed.set_author(name="f1buddy", icon_url=AVATAR_URL)
    if AVATAR_URL:
        embed.set_thumbnail(url=AVATAR_URL)
    if footer:
        embed.set_footer(text=util.clamp(footer, 2048))
    return embed


def error(message: str) -> discord.Embed:
    return make("Something went wrong", message)


def columns(embed: discord.Embed, *cols: tuple[str, list[str]]) -> discord.Embed:
    """Add inline fields, each a list of lines, cut to Discord's 1024-character limit on a line boundary."""
    for name, lines in cols:
        value = ""
        for line in lines:
            if len(value) + len(line) + 1 > 1024:
                break
            value += line + "\n"
        embed.add_field(name=name, value=value or "–", inline=True)
    return embed


def with_image(embed: discord.Embed, png: bytes, filename="plot.png") -> tuple[discord.Embed, discord.File]:
    import io
    embed.set_image(url=f"attachment://{filename}")
    return embed, discord.File(io.BytesIO(png), filename=filename)


def team_emoji(team_id) -> str:
    return EMOJIS.get(str(team_id or "").lower(), "")


def tyre_emoji(compound: str, year: int) -> str:
    name = f"tyre_{str(compound).lower()}" + ("_2018" if year == 2018 else "")
    return EMOJIS.get(name) or str(compound).title()


def _join(*parts) -> str:
    return " ".join(p for p in parts if p)


# ---------------------------------------------------------------- schedule

def session_emoji(name: str) -> str:
    if name.startswith("Practice"):
        return {"1": ":one:", "2": ":two:", "3": ":three:"}.get(name[-1], ":stopwatch:")
    if "Qualifying" in name or "Shootout" in name:
        return ":stopwatch:"
    if "Sprint" in name:
        return ":race_car:"
    if name == "Race":
        return ":checkered_flag:"
    return ":calendar:"


def offseason() -> discord.Embed:
    embed = make("Race Schedule", "It is currently off season! :crying_cat_face:",
                 "Schedule will be available 2 weeks before the first GP")
    embed.set_image(url=random.choice(OFFSEASON_GIFS))
    return embed


def schedule(view) -> discord.Embed:
    """Embed for a ScheduleView. The caller attaches view.circuit_png as circuit.png if present."""
    event = view.event
    if event is None:
        return offseason()
    flag = util.country_flag(event.country)
    short = event.name.replace("Grand Prix", "GP")
    final = event.race or event.sessions[-1]
    embed = make(_join("Race Schedule for", flag, f"**{short}**", flag), f"Race is {util.ts(final.start_utc, 'R')}!")
    columns(embed,
            ("Session", [f"{session_emoji(s.name)} {s.name}" for s in event.sessions]),
            ("Time", [util.ts(s.start_utc) for s in event.sessions]))
    if view.forecast:
        embed.add_field(name="Weather Forecast", value="​", inline=False)
        columns(embed,
                ("Day", [d.day.strftime("%A") for d in view.forecast]),
                ("Temperature", [f"{d.temp_min:.0f}–{d.temp_max:.0f} °C" for d in view.forecast]),
                ("Precipitation", [
                    f"{d.precipitation_mm:g} mm"
                    + (f" ({d.precipitation_probability}%)" if d.precipitation_probability is not None else "")
                    for d in view.forecast]))
    else:
        embed.set_footer(text="Weather forecast available within 72 hours of race")
    if view.circuit_png:
        embed.set_image(url="attachment://circuit.png")
    return embed


# --------------------------------------------------------------- standings

def _driver_cell(row, count):
    emoji = team_emoji(row.team_id)
    if count <= 22:
        return _join(emoji, row.name)
    if count <= 24:
        return _join(emoji, f"{row.given[:1]}. {row.family}")
    if count <= 26:
        return _join(emoji, row.family)
    return row.family


def wdc(s) -> discord.Embed:
    n = len(s.rows)
    drivers = [_driver_cell(r, n) for r in s.rows]
    if s.complete:
        drivers[0] += " :crown:"
    return columns(make(f"{s.year} Driver Standings"),
                   ("Position", [r.position for r in s.rows]),
                   ("Driver", drivers),
                   ("Points", [util.fmt_points(r.points) for r in s.rows]))


def wcc(s) -> discord.Embed:
    teams = [_join(team_emoji(r.team_id), r.name) for r in s.rows]
    if s.complete:
        teams[0] += " :crown:"
    return columns(make(f"{s.year} Constructor Standings"),
                   ("Position", [r.position for r in s.rows]),
                   ("Team", teams),
                   ("Points", [util.fmt_points(r.points) for r in s.rows]))


def constructors(year, rows) -> discord.Embed:
    show_emoji = len(rows) <= 11
    return columns(
        make(f"{year} Constructor Information"),
        ("Team", [_join(team_emoji(r.team_id) if show_emoji else "",
                        f"[{r.name}]({r.url})" if r.url else r.name) for r in rows]),
        ("Nationality", [_join(util.nationality_flag(r.nationality), r.nationality) for r in rows]),
        ("Championships", [str(r.titles) for r in rows]))


# ------------------------------------------------------------------ driver

def driver(p) -> discord.Embed:
    c = p.career
    fastest = "n/a" if c["fastest_laps"] is None else c["fastest_laps"]
    embed = make(_join(util.nationality_flag(p.nationality), p.name), "\n".join([
        f"**:calendar_spiral: Seasons Completed:** {c['seasons']}",
        f"**:trophy: Championships:** {c['championships']}",
        f"**:checkered_flag: Entries:** {c['entries']}",
        f"**:race_car: Starts:** {c['starts']}",
        f"**:stopwatch: Poles:** {c['poles']}",
        f"**:first_place: Wins:** {c['wins']}",
        f"**:medal: Podiums:** {c['podiums']}",
        f"**:rocket: Fastest Laps:** {fastest}",
        f"**:chart_with_upwards_trend: Points:** {util.fmt_points(c['points'])}",
    ]))
    embed.url = p.url or None
    if p.photo:
        embed.set_image(url=p.photo)
    return embed


def easter_egg(text: str) -> discord.Embed | None:
    if "anurag" in text:
        embed = make("friend anurag")
        embed.set_image(url="https://avatars.githubusercontent.com/u/100985214?v=4")
        return embed
    if text == "saul":
        embed = make("saul")
        embed.set_image(url="https://i.kym-cdn.com/entries/icons/original/000/040/009/3dsaulcover.jpg")
        return embed
    return None


# ----------------------------------------------------------------- results

def results(view, kind="Race") -> discord.Embed:
    last = "Time" if kind == "Qualifying" else "Points"
    return columns(make(f"{view.year} {view.event_name} {kind} Results"),
                   ("Position", [MEDALS.get(r.position, r.position) if kind != "Qualifying" else r.position
                                 for r in view.rows]),
                   ("Driver", [_join(team_emoji(r.team_id), r.name) for r in view.rows]),
                   (last, [r.value for r in view.rows]))


def fastest_laps(year, rows) -> list[discord.Embed]:
    chunks = [rows] if len(rows) <= 10 else [rows[:10], rows[10:]]
    embeds = []
    for i, chunk in enumerate(chunks):
        gp, lap, tyre = [], [], []
        for r in chunk:
            flag = util.country_flag(r["country"])
            if r.get("error"):
                gp.append(_join(flag, f"{r['event']} — unavailable"))
                lap.append("–")
                tyre.append("–")
                continue
            gp.append(_join(flag, team_emoji(r["team_id"]), r["code"]))
            lap.append(util.fmt_lap(r["seconds"]))
            age = f" {r['tyre_life']} laps" if r.get("tyre_life") is not None else ""
            tyre.append(tyre_emoji(r["compound"], year) + age)
        title = f"Fastest Lap {year}" + (" Continued" if i else "")
        embeds.append(columns(make(title, footer="2018 tires used" if year == 2018 else None),
                              ("GP", gp), ("Laptime", lap), ("Tyre", tyre)))
    return embeds
