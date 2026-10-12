# 03 — Plot commands

`/laptimes`, `/positions`, `/strategy`, `/qualigap`, `/consistency`, `/telemetry`, `/trackdominance`, `/avgpos`, `/h2h`.

Shared parameter rules, caching and error handling are in spec 00. Exact figure sizes, colours and titles of the old plots are in `legacy-inventory.md` section 1.3 and are kept unless this spec says otherwise.

## Open questions

1. **`/telemetry` x-axis.** The old plot uses "percentage of the lap by sample index", which misaligns two drivers at corners. Proposed: distance along the lap in metres, so braking points line up. This changes how the plot looks. OK?
2. **`/h2h` with more than two drivers in a team** (mid-season swaps). Proposed: one bar per pairing that shared at least one session, so a team can have two or three bars. The old plot assumed exactly two drivers and failed otherwise.
3. **Sprint sessions.** `/telemetry` and `/trackdominance` gain Sprint and Sprint Qualifying as session choices. `/laptimes`, `/positions`, `/strategy` and `/consistency` stay race-only as today. Want a `session` option (Race or Sprint) on those four as well?

---

## Shared plot rules (`render/style.py`, `render/plots/`)

**Structure.** Each plot is one function: `render(data: <PlotData>) -> bytes` (PNG). It creates its own `Figure` (no `pyplot` state machine), and closes it in a `finally`. The data dataclass is built by a separate `data/` function, which is where all FastF1 and pandas work happens. Tests can therefore render a plot from hand-written data.

**Style.**
- Black figure and axes background, 300 DPI.
- Fonts: `Formula1-Regular` for axis labels and ticks, `Formula1-Bold` for titles and legends.
- Watermark: the circular logo plus "Made by F1Buddy Discord Bot" in bold, placed by one helper `add_watermark(fig, corner)` at a fixed margin from the chosen corner. Every plot uses the top-left corner except `trackdominance` (bottom-left).
- Driver colour: `fastf1.plotting.get_driver_color(code, session)`. Team colour: `get_team_color(team, session)`. If a colour is unavailable the mark is white and the plot carries the note "*Some color data is unavailable".
- Clash rule for two-driver plots: if both drivers resolve to the same colour, the second is drawn white; if the first is already white, the second is grey.
- Axis ranges that depend on grid size use the number of drivers in the data, never a fixed 20.

**Cache.** PNG bytes are stored under `{DATA_DIR}/plots/` keyed as described in spec 00. Driver order is normalised in the key for symmetric plots (`VER`/`NOR` and `NOR`/`VER` share an entry).

**Embed.** The PNG is attached as `plot.png` and set as the embed image. Title and description per command below.

**Shared errors** (all `UserError`).
- Driver did not take part in the session: `{CODE} didn't take part in {year} {EventName} {Session}.`
- Two identical drivers: "Use 2 different drivers!"
- Session has no lap data: `No lap data is available for {year} {EventName} {Session}.`

**Shared AC** (apply to every plot below).
1. `render` returns PNG bytes of the expected pixel size from fixture data.
2. No figure remains open after `render`, including when it raises.
3. Rendering the same plot from two threads at once produces two correct images.
4. A second identical request is served from the cache without calling the data function.
5. A year below 2018 raises `UserError` naming 2018 (except `/avgpos` and `/h2h`).

---

## `/laptimes`

**Purpose.** Compare two drivers' lap times across a race.

**Parameters.** `driver1`, `driver2` (required), `round` (optional), `year` (optional, 2018+).

**Plot.** As legacy: two lines of lap time against lap number; x label "Lap Number (of N)"; title "{year} {Event} {D1} vs {D2}"; legend upper right. Y axis formatted `M:SS`. Laps with no time (lap 1 of a red-flag restart, for example) leave a gap in the line.

**Embed.** Title "Lap Times", description "{year} {EventName}\n{D1} vs {D2}".

**AC.** Fixture race yields two series with one point per timed lap; a driver who retired on lap 20 has a line ending at lap 20.

---

## `/positions`

**Purpose.** Position of every driver on every lap of a race.

**Parameters.** `round` (optional), `year` (optional, 2018+).

**Plot.** As legacy: one line per driver, y axis inverted with one tick per starting position, x major ticks every 5 laps; legend to the right in finishing order; title "Position Changes During {year} {Event}". Each line starts at the grid position (lap 0). Teammates share a colour; the second driver of each team is drawn dashed.

**Embed.** Title "Driver Positions", description "{year} {EventName}".

**AC.** A 20-car fixture has y ticks 1–20; a 22-car fixture has 1–22; each line's first point equals the driver's grid position.

---

## `/strategy`

**Purpose.** Tyre stints for every driver in a race.

**Parameters.** `round` (optional), `year` (optional, 2018+).

**Plot.** As legacy: one horizontal bar per driver in finishing order, one segment per stint, coloured by compound, black edges; title "{race}\nTire Strategy". The compound palette is chosen per request from the event year (2018 palette for 2018, standard palette otherwise) and passed in as data. A compound legend lists only the compounds used.

**Embed.** Title "{EventName} Tire Strategy"; footer "2018 tire colors used" for 2018 events.

**AC.**
1. Stint lengths per driver sum to that driver's completed laps.
2. A 2018 request followed by a 2024 request uses the standard palette for the second.
3. An unknown compound is drawn in the "UNKNOWN" colour, not an error.

---

## `/qualigap`

**Purpose.** Each driver's gap to pole.

**Parameters.** `round` (optional), `year` (optional, 2018+).

**Description** (fixed): "See each driver's qualifying gap to pole".

**Data.** Each driver's best time is their time in the last segment they took part in. Pole is the fastest time among drivers classified first.

**Plot.** As legacy: horizontal bars of the delta in seconds, labels "Pole", "+X.XXX", "No Time"; x axis capped at 5 seconds, with a longer gap drawn to the cap and labelled with its true value.

**Embed.** Title "Qualifying Gap to Leader", description "{year} {EventName}".

**AC.**
1. A fixture session gives pole a zero-length bar labelled "Pole" and every other bar the correct delta.
2. A driver with no time is labelled "No Time" and has no bar.
3. A session where no Q3 was run (fixture with Q3 empty) still plots, using Q2 times.

---

## `/consistency`

**Purpose.** How consistent one driver's race pace was.

**Parameters.** `driver` (required), `round` (optional), `year` (optional, 2018+).

**Data.** From the driver's race laps:
- **Outlier:** lap 1, any in-lap or out-lap, any lap not under green-flag conditions (FastF1 track status), and any lap more than 107% of the driver's median green-flag lap.
- **Mean and σ:** computed over non-outlier laps only.
- **Fastest:** the driver's fastest lap.

**Plot.** As legacy: scatter of lap time against lap number; green at or below the mean, orange above, purple fastest, red outliers, dashed grey mean line; legend outside the axes.

**Embed.** Title "{CODE} Laptime Consistency"; description "{year} {EventName}\nσ = {σ as S.mmm s}"; footer "Standard deviation (σ) & mean calculated excluding outliers".

**AC.**
1. In a fixture race with a safety car and two pit stops, exactly the in-laps, out-laps, safety-car laps and lap 1 are flagged as outliers.
2. σ equals the standard deviation of the remaining laps to the millisecond.
3. A driver with fewer than 3 non-outlier laps raises `UserError` "Not enough clean laps to measure consistency."

---

## `/telemetry`

**Purpose.** Compare speed, throttle and brake traces for one or two drivers on one lap.

**Parameters.**

| Name | Type | Required | Default |
|---|---|---|---|
| `driver1` | driver | yes | |
| `driver2` | driver | no | none (single-driver plot) |
| `round` | round | no | latest |
| `session` | session choice | no | Race |
| `year` | int, 2018+ | no | latest |
| `lap` | int | no | each driver's fastest lap |
| `ai_analysis` | bool | no | false |

**Plot.** As legacy: three stacked panels (Speed km/h, Throttle %, Brake), a dashed average-speed line per driver, suptitle "Fastest Lap Telemetry" or "Lap {N} Telemetry". X axis per open question 1. Corner numbers from FastF1 circuit info are marked along the top of the speed panel when available.

**Embed.** Title "Fastest Lap {Session} Telemetry" or "Lap {N} {Session} Telemetry". Description: "{year} {EventName}" then one line per driver `{CODE}: M:SS.mmm`.

**AI analysis.**
- Runs only when `ai_analysis` is true and `GEMINI_API_KEY` is set. If the key is not set the option still appears and the reply adds "AI analysis isn't configured on this bot."
- The plot PNG and the driver/lap summary are sent to `gemini.analyse_telemetry` with the existing "F1 race engineer" prompt.
- The result is stored in the `cache` table under the plot's cache key, so repeating a request costs nothing.
- The text is added as "AI Analysis" and truncated to fit the 4096-character description.
- An AI failure still sends the plot, with "AI analysis is unavailable right now."

**Errors.** Lap number the driver didn't complete: `{CODE} has no lap {N} in this session.`

**AC.**
1. Two-driver and one-driver fixtures both render.
2. With no `lap`, each driver's own fastest lap is used and the lap times in the description match the fixture.
3. `ai_analysis=true` with no key returns the plot and the "isn't configured" line, with no call to the Gemini module.
4. With a fake Gemini client: the first request calls it once; an identical second request doesn't call it.
5. A 6000-character AI response yields a description of at most 4096 characters.
6. The fake client raising still returns the plot.

---

## `/trackdominance`

**Purpose.** Show which of two drivers was faster on each part of the track.

**Parameters.** `driver1`, `driver2` (required), `round` (optional), `session` (optional, default Qualifying), `year` (optional, 2018+).

**Data.** Both drivers' fastest laps. The lap distance is split into 25 equal mini-sectors. For each mini-sector the winner is the driver with the higher mean speed. The track outline comes from driver 1's position data, and each outline segment takes the colour of the mini-sector that its own distance falls in (the old plot mismatched these arrays).

**Plot.** As legacy: axes off, line width 2, title "{D1} vs {D2}\n{year} {Event} {Session}\nTrack Dominance on Fastest Lap", driver legend, watermark bottom-left. The outline is rotated by the circuit's FastF1 rotation angle so it matches the usual track map orientation.

**Embed.** Title "Track Dominance During {Session}"; description "{year} {EventName}\n{D1} vs {D2}".

**AC.**
1. The data function returns exactly 25 mini-sectors, each with a winner.
2. Every outline segment's colour equals the winner of the mini-sector containing that segment's distance.
3. Swapping the driver order gives the same winners per mini-sector.

---

## `/avgpos`

**Purpose.** Average finishing or qualifying position over a season, per driver or per team.

**Parameters.**

| Name | Choices | Required | Default |
|---|---|---|---|
| `category` | Drivers, Teams | yes | |
| `session` | Race, Qualifying | yes | |
| `exclude_dnfs` | None, Mechanical only, All | no | None |
| `year` | 1950+ | no | latest |

`exclude_dnfs` replaces the old `ignore_dnfs`, whose "All / Mechanical / No" labels were ambiguous. It has no effect for Qualifying and is ignored there.

**Data.** `jolpica.season_results(year)` or `season_qualifying(year)` — a handful of requests for the whole season, not one session load per round.
- A DNF is any result whose status is not "Finished" or a "+N Lap(s)" classification.
- A mechanical DNF is a DNF whose status is not in the driver-caused set: Accident, Collision, Collision damage, Spun off, Disqualified, Did not start, Did not qualify, Withdrew, Illness, Injury. Classifying by exclusion means a new mechanical status string needs no code change.
- Teams: the mean over all of the team's entries.
- A driver with no counted results is left out.

**Plot.** As legacy: horizontal bars sorted best to worst, value after each bar to 2 decimals, title "Average {Drivers|Teams} {Qualifying|Race} Finish Position {year}" plus " (DNF/DNS Excluded)", " (Mechanical DNFs Excluded)" or " (DNFs Included)". X axis runs to the largest grid size of the season.

**Embed.** Title as the plot title without the suffix; description "DNF/DNS excluded from calculation", "Mechanical DNFs excluded from calculation" or "DNFs included in calculation".

**AC.**
1. For a three-race fixture, each driver's average equals the hand-computed value under each `exclude_dnfs` setting.
2. A status of "Engine" counts as mechanical; "Collision" does not.
3. The final round of a completed season is included.
4. A new round completing changes the cache key.
5. A pre-2018 season renders, with white bars and the colour note where colours are unavailable.

---

## `/h2h`

**Purpose.** Teammate head-to-head record over a season.

**Parameters.** `session` (Race or Qualifying, required), `exclude_dnfs` (bool, optional, default false; races only), `year` (optional, 1950+).

**Data.** `jolpica.season_results` or `season_qualifying`. For each team and each pair of its drivers, count the rounds where both took part and one finished ahead. With `exclude_dnfs`, a round where either driver retired is not counted. A team with one entry in a round contributes nothing for that round and the other teams are unaffected.

**Plot.** As legacy: one back-to-back bar per pairing with the team logo at the centre (team name as text if there is no logo), win counts at the bar ends, driver codes at the edges, suptitle "{year} {Session} Head to Head (Retirements Excluded|Included)". Pairings are ordered by constructor standing. See open question 2 for teams with more than two drivers.

**Embed.** Title "{year} {Session} Head to Head"; footer "All retirements excluded" or "Retirements included".

**AC.**
1. For a three-race fixture, each pairing's score equals the hand-computed value, with and without `exclude_dnfs`.
2. A round where one team entered a single car leaves every other team's score correct.
3. A team with a mid-season driver swap produces one bar per pairing that shared a round.
4. A team with no colour or no logo renders with white bars or a text label.
5. The final round of a completed season is included.
