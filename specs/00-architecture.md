# 00 — Architecture

Applies to every other spec. Current behaviour of the old bot is in `legacy-inventory.md`.

## Open questions

1. **Embed colour.** `lib/colors.py` is lost. Proposed default: `#E10600` (F1 red). Do you have the old file, or a preferred colour?
2. **Custom emoji artwork.** Which server owns the current team and tyre emojis? The images need exporting once so they can be re-uploaded as application emojis (see "Emojis").
3. **Admin ids.** The three hardcoded admin user ids move to config. Are all three still admins?

## Goals

- Every command in the legacy inventory keeps its name and capability.
- No command depends on scraping HTML except FIA documents.
- Everything except the final Discord round trip is testable offline with no token.
- One external source failing degrades one feature, never the bot.

## Stack

| Item | Choice |
|---|---|
| Python | 3.12 |
| Discord | discord.py 2.x |
| F1 data | FastF1 ≥ 3.8 (pinned exactly in `requirements.txt`) |
| HTTP | `httpx` (async) for everything FastF1 doesn't cover |
| Storage | SQLite via stdlib `sqlite3`, called through `asyncio.to_thread` |
| Plots | matplotlib (Agg backend, object-oriented API only) |
| PDF | PyMuPDF |
| HTML | beautifulsoup4 (FIA documents only) |
| Tests | pytest, pytest-asyncio |

Dropped from the old bot: `pytube`, `wikipedia`, `Unidecode`, `country_converter`, `pycountry`, `google-generativeai` (replaced by `google-genai`, optional), `requests`.

## Layout

```
f1buddy/
  __main__.py        start-up: config, db, load cogs, run
  config.py          environment variables → frozen dataclass
  db.py              connection, schema, migrations
  errors.py          UserError and subclasses
  series/            series provider interface + f1.py
  sources/           one module per external source (see 01)
  data/              pure functions: source data → result dataclasses
  render/
    embeds.py        result dataclass → discord.Embed
    plots/           result dataclass → PNG bytes, one module per plot
    style.py         fonts, watermark, colours
  cogs/              thin: parse input, call data, call render, send
  assets/            fonts, watermark, team logos, help screenshots
tests/
  fixtures/          recorded API responses, HTML pages, PDFs
specs/
Dockerfile
compose.yaml
requirements.txt
```

**Layer rules**
- A cog function does four things: resolve parameters, call one `data` function, call one `render` function, send. It contains no HTTP, no pandas and no matplotlib.
- `data` functions take already-fetched source objects or call a `sources` function. They return frozen dataclasses and never touch Discord types.
- `render` functions are pure: dataclass in, `discord.Embed` or `bytes` out.
- Blocking work (FastF1 loads, plotting, PDF rendering, SQLite) runs through `asyncio.to_thread`.
- No module-level mutable state and no time captured at import. "Now" is passed in or read at call time, so tests can fix it.

## Series support

The bot must be able to gain other series later without changing cogs. Only the schedule is series-dependent today, so the interface is small on purpose:

```python
class Series(Protocol):
    key: str            # "f1"
    name: str           # "Formula 1"
    async def season_schedule(self, year: int) -> list[Event]: ...
```

`Event` and `SessionSlot` are the dataclasses defined in spec 02 (`/schedule`). Reminders (05) and predictions (06) store `series` as a column so they work for any provider. Only `series/f1.py` is written. F1-only commands (plots, telemetry) call FastF1 directly and make no attempt to be generic.

## Configuration

Environment variables, loaded once into a frozen dataclass. A missing required variable stops start-up with a message naming it.

| Variable | Required | Purpose |
|---|---|---|
| `DISCORD_TOKEN` | yes | Bot token |
| `ADMIN_USER_IDS` | yes | Comma-separated user ids allowed to run `f1$sync` |
| `OWNER_ALERT_CHANNEL_ID` | no | Channel for operational alerts (scraper failures) |
| `GEMINI_API_KEY` | no | Enables `/telemetry` AI analysis |
| `GEMINI_MODEL` | no | Model used for the analysis |
| `OPENF1_USERNAME`, `OPENF1_PASSWORD` | no | Enables live session info (spec 07) |
| `DATA_DIR` | no (default `./data`) | SQLite file, FastF1 cache, plot cache, FIA page cache |
| `LOG_LEVEL` | no (default `INFO`) | |

`.env` is read by Docker Compose only and is never committed. `.env.example` lists every variable.

Per-server settings live in SQLite and are set with admin slash commands (specs 04 and 05).

## Storage

One SQLite file at `{DATA_DIR}/f1buddy.db`. Schema is created at start-up; `PRAGMA user_version` tracks the version and migrations are plain SQL run in order. Tables are defined in the spec that owns them:

| Table | Spec |
|---|---|
| `guild_settings` | this spec |
| `cache` | 01 |
| `fia_documents`, `fia_posts` | 04 |
| `reminder_subscriptions`, `reminders_sent`, `weekend_posts` | 05 |
| `predictions`, `prediction_scores` | 06 |

```sql
CREATE TABLE guild_settings (
  guild_id            INTEGER PRIMARY KEY,
  fia_channel_id      INTEGER,
  reminder_channel_id INTEGER,
  reminder_role_id    INTEGER,
  weekend_channel_id  INTEGER,
  live_channel_id     INTEGER
);
```

**Caches on disk** (all under `DATA_DIR`, all safe to delete):
- `fastf1/` — FastF1's own cache.
- `plots/` — PNGs keyed by a hash of (plot name, year, round number, session, every other parameter). A plot for a completed session never changes, so entries have no expiry. Season-aggregate plots (`avgpos`, `h2h`) include the latest completed round in the key.
- `fia/` — rendered document pages, keyed by document id.

## Shared parameter rules

These replace the per-cog copies in the old bot.

- **`year`** — optional integer everywhere. Default: the season of the most recently completed session of the relevant type. Minimum 1950 for results and standings, 2018 for anything needing lap or telemetry data. A year outside the range is an error naming the valid range. It is never silently replaced.
- **`round`** — optional string everywhere: a round number or an event name. Default: the most recently completed round of the relevant session type. Autocomplete lists the season's events as "{n}. {EventName}", filtered by the text typed so far. A round that hasn't happened yet is an error saying so.
- **`driver`** — string. Autocomplete lists the drivers of the selected season as "{CODE} — {Full Name}" and returns the code. Free text is still accepted and matched against code, surname or full name, ignoring case and accents.
- **`session`** — choice: FP1, FP2, FP3, Sprint Qualifying, Sprint, Qualifying, Race. A session the event doesn't have is an error listing the ones it has.
- **Parameter order** in every command: subject (drivers), then `round`, `session`, `year`, then command-specific options.
- **Latest completed round** returns `n` for a finished season (the old helper returned `n-1`).

## Error handling

- `UserError(message)` is raised for anything the user can fix (bad year, unknown driver, session not run yet). A single app-command error handler turns it into an ephemeral embed with that message.
- `SourceError(source, detail)` is raised when an external source fails. The handler replies "Couldn't reach {source}. Try again in a few minutes." and logs the detail.
- Anything else is logged with a traceback and the user gets "Something went wrong. It's been logged." No traceback is ever sent to Discord.
- Every command defers first, so there is always a reply.
- A cog that fails to load is logged and skipped; the bot still starts.
- Embeds are built through one helper that truncates descriptions to 4096 characters and field values to 1024, and splits attachments into messages of at most 10 files.

## Emojis

Team and tyre emojis are uploaded as **application emojis** (owned by the bot, usable in every server). `scripts/upload_emojis.py` uploads every image in `assets/emojis/` under its file name. At start-up the bot fetches its application emojis into a name → emoji map. A missing emoji renders as nothing, never as an error.

Team emoji names are derived from the FastF1 `TeamId` (for example `red_bull`), so a new team needs one new image and no code change.

## Embeds

- Author "f1buddy" with the bot's avatar; thumbnail is the bot's logo. Both are attached from `assets/` or read from the bot user, not from a hardcoded CDN URL.
- Colour from the open question above.
- Error embed: title "Something went wrong", no GIF.

## Testing

No test needs a Discord token or network access.

| Layer | How it's tested |
|---|---|
| `sources` | Parsers run against recorded responses in `tests/fixtures/`. HTTP is replaced by an `httpx.MockTransport`. |
| `data` | Called with fixture-backed source objects; assertions on the returned dataclasses. FastF1 sessions come from a small committed cache (one conventional weekend, one sprint weekend). |
| `render/embeds` | Assertions on the `discord.Embed` fields. |
| `render/plots` | Each plot renders from fixture data to PNG bytes without error, with the expected pixel size. A `--save-plots` flag writes them to a folder for a visual check. |
| `cogs` | Command callbacks are called with a fake `Interaction` that records `defer` and `followup.send` calls. |
| Background tasks | The loop body is a plain coroutine taking a clock and a sender, called directly with fakes. |

**Live canary.** `pytest -m live` runs each source against the real service and checks only that the parsed result has the expected shape. It is excluded by default and is how a site change is detected before users notice.

**Manual checks** (need a token, done once tokens are provided): command sync, emoji rendering, attachment sending, message publishing in an announcement channel, reminder pings.

## Deployment

- `Dockerfile`: `python:3.12-slim`, install `requirements.txt`, copy the package, run `python -m f1buddy` as a non-root user.
- `compose.yaml`: one service, `env_file: .env`, a named volume mounted at `/data`, `restart: unless-stopped`.
- Update procedure for the host: `git pull && docker compose up -d --build`.
- Slash commands are synced by `f1$sync` (kept), not automatically at start-up.

## Definition of done (per command or feature)

1. Its acceptance criteria pass as automated tests.
2. It has a `-m live` canary if it uses an external source.
3. It has no entry in the manual-check list that hasn't been run, once tokens exist.
4. `/help` documents it.

## Legacy coverage

| Legacy item | Spec |
|---|---|
| `/schedule`, `/wdc`, `/wcc`, `/constructors`, `/driver`, `/results`, `/qualifying`, `/fl`, `/help`, `/lightsout`, `f1$sync` | 02 |
| `/laptimes`, `/positions`, `/strategy`, `/qualigap`, `/consistency`, `/telemetry`, `/trackdominance`, `/avgpos`, `/h2h` | 03 |
| `/fiadoc`, FIA poller | 04 |

| Defect | Resolved by |
|---|---|
| D1, D2, D26 | Error handling (this spec) |
| D3, D13, D14, D22 | Layer rules (this spec) |
| D5, D6, D7, D23, D24, D25 | 02 |
| D4, D11, D12, D15, D16, D17, D18, D19, D21 | 03 |
| D8, D9, D10 | 04 |
| D20 | Not applicable: old `lib/` code is not carried over |
