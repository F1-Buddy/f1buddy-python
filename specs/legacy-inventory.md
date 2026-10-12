# Legacy inventory (pre-rewrite bot, last commit 2024-07-11)

Reference for what the old bot does. Produced by reading every source file; `.env`, `config.py` and asset folders were not opened.

- **[V]** verified by reading the code.
- **[I]** inferred, or based on knowledge of library and site behaviour.

## 0. Headline findings

1. **`lib/colors.py` does not exist.** It is gitignored and absent from the working tree. `from lib.colors import colors` (exposing `.default`, and `.hot_pink` in a dead file) is imported by `repeated/embed.py` and most cogs, so a fresh checkout cannot load them. [V]
2. **Ergast is dead.** `constructor.py` calls `ergast.com` directly. `wdc`/`wcc` use `fastf1.ergast.Ergast`, which depends on the installed FastF1 version. [I]
3. **`fiadocs.py:createDocThread` never returns.** `on_ready` awaits it, so the poller runs inside `on_ready` and the `threading.Thread` line is never reached. [V]
4. **Many error paths are broken.** Several commands return a bare embed where the caller unpacks a tuple, so errors become unhandled exceptions with no reply (section 6).
5. **`/qualigap` has the wrong description**, copy-pasted from `/positions`. [V]

## 1. Command inventory

Bot: `commands.Bot(command_prefix='f1$')`, intents default + `message_content` + `members`. No buttons, views, pagination, autocompletes, cooldowns, checks or `tasks.loop`. Slash commands are synced only by `f1$sync`. 20 live slash commands, 1 prefix command.

### 1.1 Prefix command

**`f1$sync`** (`cogs/sync.py`)
- Hardcoded admin ids: `235835251052642315`, `308274708262944769`, `403699636612890624`.
- Admin: sets presence Listening "V10s | /help | N servers"; runs `bot.user.edit(username='F1Buddy')` (rate-limited, no try/except); runs global `tree.sync()`; replies "`@user synced N commands`".
- Otherwise replies "`<user> is not a bot admin! Can't sync :(`".

### 1.2 Slash commands

**1. `/schedule`** — "get F1 race schedule". No parameters.
- Loads `fastf1.get_event_schedule(now.year, include_testing=False)`; `now` is New York time.
- Offseason (`any(cm.currently_offseason())`): `OffseasonEmbed`: title "Race Schedule", description "It is currently off season! :crying_cat_face:", a random one of 5 tenor GIFs, footer "Schedule will be available 2 weeks before the first GP".
- Otherwise next event = `latest_completed_index(year) + 1` (min 1).
- Session rows: conventional weekends use emojis one, two, three, stopwatch, checkered_flag; other formats use one, stopwatch, stopwatch, race_car, checkered_flag. Names from `SessionN`, times from `SessionNDateUtc` as `<t:epoch:f>` (viewer-local).
- Title `"Race Schedule for :flag_xx:**<EventName minus ' Grand Prix'> GP**:flag_xx:"`. Flag from `coco.convert(Country, to="ISO2")`; Abu Dhabi special-cased to `:flag_ae:`; otherwise no flag.
- Description `Race is <t:race_ts:R>!`.
- Image: circuit image URL scraped from formula1.com. Two inline fields "Session" and "Time".
- Race within 72 h: adds "Weather Forecast:" (blank), "Day" (fixed "Friday\nSaturday\nSunday"), "Temperature" (`avgtemp_c °C` per day), "Precipitation" (`totalprecip_mm mm` per day). Otherwise footer "Weather forecast available within 72 hours of race*".
- Any exception becomes `ErrorEmbed(error_message=e)`.

**2. `/wdc`** — "Get driver standings". `year: Optional[int]`.
- `cm.check_year(year, False, False)`: `None` → latest valid year; valid range 1958..limit; otherwise ErrorEmbed "Invalid Input: <year>".
- `Ergast().get_driver_standings(season=year)`. Inline columns "Position", "Driver" (team emoji + name), "Points" (int when whole).
- Name shortening by driver count: ≤22 emoji + full name; 23-24 emoji + initial + surname; 25-26 emoji + surname; >26 plain name.
- `:crown:` on the champion when `year != now.year`. Driver column truncated at 1024 chars. Team is `constructorNames[0]`.

**3. `/wcc`** — "Get constructor standings". `year: Optional[int]`.
- Same year check; `Ergast().get_constructor_standings`. Columns "Position", "Team Name" (emoji + name, `:crown:` for a past-season winner), "Points".
- `year == 2007`: `team_position[10] = "EX"` (McLaren excluded).

**4. `/constructors`** — "Get constructor information". `year: Optional[int]` (not validated when given).
- `http://ergast.com/api/f1/{year}/constructors.json`. Title "{season} Constructor Information".
- Fields: "Team" (emoji if ≤11 teams, name linked to Wikipedia `url`), "Nationality" (flag + nationality, via `lib/nation.csv` + `coco`), "Championships" (hardcoded `lib/championship.py`, current to 2022, else "0").

**5. `/driver`** — "Get driver info". `driver: str` (full name, no autocomplete).
- Easter eggs before lookup: `'anurag' in driver` → embed "friend anurag" with a GitHub avatar; `driver == 'saul'` → embed "saul" with a kym-cdn image.
- Scrapes Wikipedia's list of F1 drivers; matches a row by `unidecode(name).casefold()` equality (exact full name).
- Found: title = name linked to Wikipedia; image = page's original image; thumbnail = nationality flag; description lines Seasons Completed, Championships, Entries, Starts, Poles, Wins, Podiums, Fastest Laps, Points, each with an emoji.
- Not found: title `Driver "<name>" not found!`, description "Try a driver's full name!", error GIF.

**6. `/results`** — "Get results of a specific race or the latest by leaving all options blank". `year: Optional[int]`, `round: Optional[str]` (name or number).
- Year `None`, ≤1957 or ≥ current year is silently replaced by the current year (minus 1 in pre-season).
- Round `None` → latest completed race. Future race → ErrorEmbed "Race hasn't happened yet!!".
- Embed "{year} {EventName} Race Results". Fields "Position" (medal emojis for P1-3), "Driver" (team emoji + full name), "Points" (trailing `.0` stripped). Footer "*Highlights video link below may not be accurate".
- Second message: a YouTube highlights URL.

**7. `/qualifying`** — "Get results of a qualifying session or the latest by leaving all options blank". Same parameters. (`help.py` documents it as `quali`.)
- Fields "Position", "Driver" (team emoji), "Time" (`Q3: m:ss.mmm`, falling back to Q2, Q1, then "Q1: No Time").
- Second message: YouTube URL for "{year} {EventName} Qualifying".

**8. `/fl`** — "Get fastest lap". `round: Optional[str]`, `year: Optional[int]` (2018+).
- Year out of range → generic ErrorEmbed with no message. Round above latest completed → "Bad Round" / "Round N hasn't occured yet!".
- `round=None`: loops every completed round (slow, sequential); a failed round is logged and skipped.
- Per round from `laps.pick_fastest()`: "GP Name" (flag emoji, team emoji, driver code), "Laptime" (`MM:SS.mmm`), "Age" (tyre compound emoji + `TyreLife`).
- More than 10 rows → two embeds "Fastest Lap {year}" and "… Continued" in one message. Footer "{year} tires used" when `year <= 2018`.

**9. `/fiadoc`** — "Get latest FIA Document". `doc: Optional[int]` ("Go back X documents"; default 0 = newest).
- Scrapes the FIA season page, downloads PDF number `doc`, renders every page to a 300 DPI PNG (PyMuPDF), caches PNGs in `cogs/fiaDocs/<name>/<n>.png`.
- Embed title "Latest FIA Document" or "FIA Document {doc}"; description = file name without `.pdf`. All pages attached to one message.
- `IndexError` → "Document doesn't exist!".

**10. `/laptimes`** — "Compare laptimes of two drivers in a race (2018 onwards)". `driver1: str`, `driver2: str` (3-letter codes), `round: str` (required), `year: Optional[int]`.
- Same driver twice → "Use 2 different drivers!". Failure footer "Likely an unsupported input (year/round) was given \n *(2018+)*".

**11. `/positions`** — "See driver position changes over the race". `round: str`, `year: Optional[int]`. Embed title "Driver Positions", description "{year} {EventName}".

**12. `/strategy`** — "See tire strategies for the race". `round: str`, `year: Optional[int]` (2018+). Title "{racename} Tire Strategy"; footer "2018 tire colors used" for 2018.

**13. `/qualigap`** — description wrongly "See driver position changes over the race". `round: str`, `year: Optional[int]`. Title "Qualifying Gap to Leader", description "{year} {EventName}".

**14. `/consistency`** — "Plot driver laptime consistency". `driver: str`, `round: Optional[str]`, `year: Optional[int]` (2018+).
- Title "{DRIVER} Laptime Consistency"; description "{year} {EventName}\nσ = {std}" (σ excludes lap 1 and slow laps, `MM:SS.mmm`); footer "Standard deviation (σ) & mean calculated excluding outliers".
- Future race → "Race hasn't happened yet!!".

**15. `/telemetry`** — "Compare telemetry between 2 drivers on a specific lap, leave blank for respective fastest laps".
- Parameters in order: `driver1: str`, `ai_analysis: Choice` (True/False, required), `driver2: Optional[str]`, `lap_number: Optional[int]`, `round: str`, `year: int` (required), `sessiontype: Choice` (FP1, FP2, FP3, Qualifying, Race).
- Year outside 2018..now → "Enter a valid year from 2018 to now". Same driver → "Use 2 different drivers!". Bad round → "Error getting round, likely bad input given".
- Title "Fastest Lap {Qualifying} Telemetry" or "Lap {N} Telemetry". Description: `str(session)` then `<DRV>: m:ss.mmm` per driver; with AI on, appends `AI Analysis: <Gemini text>`.

**16. `/trackdominance`** — "See track dominance between drivers on their personal fastest laps". `driver1: str`, `driver2: str`, `round: str`, `sessiontype: Choice` (FP1, FP2, FP3, Qualifying, Race), `year: Optional[int]`.
- Title "Track Dominance During {session}"; description "{year} {EventName}\n{D1} vs {D2}".

**17. `/avgpos`** — "See average finish position for driver for race/qualifying throughout the year".
- `category: Choice` (Drivers | Teams), `session_type: Choice` (Qualifying | Race), `ignore_dnfs: Choice` ("All" = exclude all DNFs, "Mechanical" = exclude mechanical DNFs, "No" = include), `year: Optional[int]` (1958+).
- Title "Average {category} {SessionName} Finish Position {year}". Description "DNF/DNS excluded from calculation" | "Mechanical DNFs excluded from calculation" | "DNFs included in calculation".

**18. `/h2h`** — "See head to head stats of specific drivers or teammate pairings." `year: Optional[int]`, `session_type: Choice` (Race | Qualifying), `ignore_dnfs: Choice` (Yes | No).
- Teammate head-to-head bar plot. Title "{year} {Session} Head to Head"; footer "All retirements excluded" or "Retirements Included".

**19. `/lightsout`** — "Wait for the lights and react the fastest!" No parameters.
- Sends embed "Lights out!" with a 2×5 grid of black circles and adds a 🏎️ reaction. Each second for 5 s one more column turns red (message edit). Waits a random 0.00-5.99 s, resets the grid to black with `:green_square:` and `:dash:`, then waits for the first 🏎️ reaction (no timeout, no message check, no bot filter).
- Winner: title "And away we go!", description "`<mention>` got away the fastest!" with a checkered flag, footer "Lights held for {delay} seconds".

**20. `/help`** — "get help". `command_name: Optional[str]`.
- Embed "f1buddy Help" (or "f1buddy Help - {name}") with usage text and a screenshot from `images/<file>.png`.
- Unknown name: "Command '<x>' not recognized…" with `images/laeppa-vika-half-life-alyx.gif`.
- Stale: documents `quali` (command is `qualifying`), `fl` "default year 2023", old `avgpos`/`h2h`/`telemetry` parameters; `lightsout` undocumented. Links `https://discord.gg/Qx3gqWrpzJ` and the GitHub issues page.

### 1.3 Plot styling

**Shared**
- Black figure and axes. Fonts from `lib/fonts/Formula1-{Regular,Bold,Black,Wide}.ttf`: Regular for labels and ticks, Bold for titles and legends.
- Watermark: `botPics/f1pythoncircular.png` near the top-left or bottom-left with the text "Made by F1Buddy Discord Bot" in bold. Offsets differ per plot.
- 300 DPI. Team colours from `results['TeamColor']`. Two drivers with the same colour: the second becomes white (grey if the first is already white).

**Per plot**
- **laptimes**: 9×6, two lines of `LapTime` vs `LapNumber`; xlabel "Lap Number (of N)"; title "{year} {Event} {D1} vs {D2}"; legend upper right.
- **positions**: 10.6×6.5, one line per driver of `Position` vs `LapNumber`; y inverted, ticks 1..20; x major ticks every 5, minor every 1; legend to the right; title "Position Changes During {year} {Event}".
- **strategy**: 10×10, horizontal bar per driver in finishing order, one segment per stint coloured by compound with a black edge; title "{race}\nTire Strategy" (size 20); x ticks every 10, minor every 2.
  - 2019+: SOFT `#da291c`, MEDIUM `#ffd12e`, HARD `#f0f0ec`, INTERMEDIATE `#43b02a`, WET `#0067ad`, UNKNOWN `#00ffff`, TEST-UNKNOWN `#434649`.
  - 2018: SOFT yellow, MEDIUM white, HARD `#0096FF`, HYPERSOFT pink, ULTRASOFT purple, SUPERSOFT red, SUPERHARD orange.
- **qualigap**: 8.25×5.5, horizontal bars of delta to pole (s); labels "   Pole", "+X.XXX", "No Time"; x capped at `min(max(delta), 5)`.
- **consistency**: 9×6 scatter of lap time vs lap number. Green `#00ff00` ≤ mean, orange `#ffaf00` slower, purple `#B138DD` fastest, red `#F91536` outliers (pit-out laps or ≥10 s over the mean), dashed grey `#969696` mean line. Y ticks `MM:SS`. Legend (Average, Fastest, Quicker, Slower, Outlier) outside the axes.
- **telemetry**: 13×9, three stacked panels (Speed km/h, Throttle %, Brake Off/On). X = fraction of the lap as a percentage (not distance). Dashed average-speed line per driver. Suptitle "Fastest Lap Telemetry" or "Lap N Telemetry". Legend of colour patches.
- **trackdominance**: 7.5×6, axes off. Track drawn from driver 1's fastest-lap X/Y, split into 25 mini-sectors by distance; each coloured by the driver with the higher mean speed. Line width 2. Title "{D1} vs {D2}\n{year} {Event} {Session}\nTrack Dominance on Fastest Lap". Driver legend.
- **avgpos**: 16.8×10.5, horizontal bars sorted by average, value printed after each bar (2 dp); title "Average {Drivers|Teams} {Qualifying|Race} Finish Position {year}" + " (DNF/DNS Excluded)" | " (Mechanical DNFs Excluded)" | " (DNFS Included)"; y inverted; missing colour → white bar + "*Some color data is unavailable".
- **h2h**: 13×9, back-to-back bar per teammate pairing with the team logo (`lib/cars/logos/{TeamId}.webp`, 64 px) at the centre (team id as text if missing); win counts at bar ends (size 20), driver codes at the plot edges; black text stroke; suptitle "{year} {Session} Head to Head (Retirements Excluded|Included)".

### 1.4 Dead / unregistered commands

`schedule.pydeprecated` (`/schedulef1`), `results.pydeprecated`, `qualifying.pydeprecated` (`/quali`), `avgpos.pydeprecated`, `avggapteam.pydeprecated` (`/avggaps`), `h2h.pyfixlater`, `cogsmotogp/scheduleMGP.py` (`/schedulemotogp`, never loaded).

## 2. Data sources

| Command / task | Source |
|---|---|
| `/schedule` | FastF1 schedule; formula1.com circuit page (scrape); RapidAPI weatherapi |
| `/wdc`, `/wcc` | `fastf1.ergast.Ergast` |
| `/constructors` | `ergast.com` JSON; `lib/nation.csv`; `lib/championship.py` |
| `/driver` | Wikipedia table scrape; `wikipedia` package; Wikipedia pageimages API |
| `/results`, `/qualifying` | FastF1 results; YouTube search via `pytube` |
| `/fl` | FastF1 laps; `pycountry` |
| `/fiadoc`, poller | fia.com HTML scrape; PDF download; PyMuPDF |
| plot commands | FastF1 session data |
| `/telemetry` AI | Google Gemini (`google.generativeai`, `gemini-1.5-pro-latest`) |
| `/lightsout`, `/help`, `f1$sync` | Local only |

**Scraping details (the fragile parts)**
- **formula1.com**: `https://www.formula1.com/en/racing/{year}/{Name}/Circuit.html`; `soup.find_all(class_="f1-c-image")`, first `src` containing "circuit". Two candidate URLs are tried but only the last one's result is evaluated (bug).
- **fia.com**: hardcoded `https://www.fia.com/documents/championships/fia-formula-one-world-championship-14/season/season-2024-2043`; `find_all(class_='document-row')` → `find('a')['href']`; file name = text after `/sites/default/files/decision-document/`.
- **Wikipedia**: `https://en.wikipedia.org/wiki/List_of_Formula_One_drivers`, first `table.wikitable.sortable`, fixed cell indices `[0]` name, `[2]` seasons, `[3]` championships, `[4]` entries, `[5]` starts, `[6]` poles, `[7]` wins, `[8]` podiums, `[9]` fastest laps, `[10]` points. Championships keeps only the first character.
- **Weather**: `GET https://weatherapi-com.p.rapidapi.com/forecast.json?q=<Location>, <Country>&days=3`, no error handling.
- **YouTube**: `pytube.Search(...).results[0]`, id extracted by string slicing.
- **Gemini**: prompt asks for an "F1 Race Engineer" style analysis of the telemetry plot image.

**Secrets referenced**: `config.TOKEN`, `config.weatherapiKEY`, `config.GEMINI_KEY`. `.env` is not read by any code.

## 3. Background tasks and state

**FIA docs poller (`fiadocs.py`)**
- Runs inside `on_ready`, forever. Channel id `1212636200217878528` hardcoded.
- Each iteration checks only the newest document; new = directory `cogs/fiaDocs/<fileName>` missing. Posts embed "Latest FIA Doc" with `[docName](url)` and all page images, then `message.publish()`.
- Sleeps 30 s on success. **No sleep on exception** (hot loop). Blocking I/O in an `async def`.
- Directory is created before the download, so a failed download is never retried. Two documents within one interval → the older is missed. More than 10 pages → the send fails silently.
- State is only the directory tree in `cogs/fiaDocs/`; the poller and `/fiadoc` use different directory keys and don't share it.

**Other state**: FastF1 cache in `cache/`; plot PNG caches in `cogs/plots/<name>/` (never invalidated; some keyed by a 12-hour-clock timestamp); module-global embeds and `now` timestamps captured at import.

**Hardcoded**: admin user ids (above); FIA channel id; custom emoji ids in `lib/emojiid.py` (41 team keys covering ~2010-2024, tyre compounds, 2018 tyre set), which resolve only if the bot is in the owning server; all paths relative to the repo root; prefix `f1$`; name `F1Buddy`.

## 4. Shared code

- `repeated/common.py`: `currently_offseason()`, `latest_completed_index(year)`, `latest_quali_completed_index(year)`, `check_year(year, data, quali)`. **`latest_completed_index` returns n-1 for a finished season**, so the last race is excluded from `/fl`, `/avgpos`, `/h2h` and default `/results`.
- `repeated/embed.py`: `Embed`, `ErrorEmbed` (title "Error Occured :(" + error GIF), `OffseasonEmbed`. Default author "f1buddy", default thumbnail a Discord-CDN URL.
- `cache.py`: standalone script that pre-warms the FastF1 cache.
- `lib/`: `f1font.py` (fonts), `emojiid.py` (emoji ids, `nation_dictionary()`), `championship.py` (stale), `drivernames.py`, `station_codes.py`, `teamcolors.*` (all three unused by live code), `nation.csv` (demonym → place, 2157 rows).
- Duplicated across cogs: year resolution, round parsing, plot-and-cache pattern, watermark block, lap-time formatting, same-colour rule, session-type choices, FIA PDF rendering (three copies).

## 5. Dependencies (requirements.txt is empty)

`discord.py` 2.x, `fastf1` 3.x, `pandas`, `numpy`, `matplotlib`, `Pillow`, `requests`, `beautifulsoup4`, `PyMuPDF`, `pytube`, `wikipedia`, `Unidecode`, `country_converter`, `pycountry`, `google-generativeai`. Python ≥ 3.10 (`match`/`case`).

Retired or deprecated in use [I]: Ergast host; `Laps.pick_driver`/`pick_lap` (singular forms); `fastf1.plotting.driver_color`, `_enable_fastf1_color_scheme`; `pytube`; `google.generativeai` and `gemini-1.5-pro-latest`.

## 6. Defects

- **D1** Error returns have inconsistent shapes (`results2`, `quali2`, `consistency`, `h2hnew`, `fastest_lap`, `driver`), so errors raise and the user gets a traceback embed or no reply.
- **D2** `help.py` error path references unbound variables.
- **D3** `loop.close()` on the running loop after every reply (17 places).
- **D4** `consistency.py` outlier filter raises and is swallowed, so every lap is drawn as an outlier; recursive calls discard results.
- **D5** `driver.py`: wrong `set_footer` call, `nationality` unbound without a flag, exact-full-name match only, championships ≥10 misread.
- **D6** `results2.py`: bare excepts; round 0 requested in pre-season; future/invalid year silently remapped.
- **D7** `schedule.py`: only the last circuit URL parsed; sprint icons only fit the 2023 format; fixed Friday/Saturday/Sunday labels over a forecast starting today; a weather failure kills the command; no reply if the send fails.
- **D8** FIA poller: runs in `on_ready`, hot loop on error, blocking I/O, newest-only, no retry, hardcoded 2024 season URL, `publish()` needs an announcement channel, 10-attachment limit.
- **D9** `/fiadoc`: cached pages listed unsorted (page order wrong on re-request); negative `doc` indexes from the end.
- **D10** Poller and command use different cache keys.
- **D11** `strategy.py`: the 2018 palette sticks globally after one 2018 request.
- **D12** `laptimes.py`: out-of-range year loads without laps; plotting state set at import; cache not keyed by year.
- **D13** `now` frozen at import in 10 modules, so season boundaries are wrong after New Year.
- **D14** Module-global embeds and global pyplot state shared across concurrent requests; figures leaked.
- **D15** `speed.py`: colour array and track segments misaligned.
- **D16** `qualigap.py`: fails when pole has no Q3 time; fixed 20-row axis; wrong description.
- **D17** `positions.py`: axis hardcoded to 20 positions.
- **D18** `telemetry.py`: AI text regenerated on every call; description can exceed 4096 chars; no sprint sessions.
- **D19** `avgpos2.py`: cache keyed by race index for qualifying; mechanical-DNF list is four exact strings.
- **D20** Unused data and functions throughout `lib/`.
- **D21** `h2hnew.py`: `break` where `continue` is meant; fails on a missing team colour; assumes two drivers per team; `ignore_dnfs` is a no-op for qualifying; slow sequential loads.
- **D22** `main.py`: one broken cog stops start-up.
- **D23** `sync.py`: username edit failure prevents the sync.
- **D24** `lightsout.py`: no timeout, no message check.
- **D25** `constructor.py`: flag lookup raises when a demonym maps to several places.
- **D26** Discord limits unhandled: 4096-char descriptions, 1024-char fields, 10 attachments, file size.

## 7. Git history

665 commits, 2022-12-27 to 2024-07-11. Schedule and FIA docs show constant fix commits, the FIA ones ending with "still not fixed".
