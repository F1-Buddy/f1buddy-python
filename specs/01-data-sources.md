# 01 — Data sources

One module per source in `f1buddy/sources/`. Nothing outside `sources/` makes a network call. Each module exposes plain functions returning dataclasses or FastF1 objects, and raises `SourceError` on failure.

## Decisions

- **Fastest laps before 2004:** accepted. `/driver` shows "n/a" for careers that ended before 2004.

## As built: differences from this spec

- **Jolpica is called directly with `httpx`**, not through `fastf1.ergast`. This makes it async, cacheable in SQLite and testable with a mock transport.
- **Jolpica requires a season for standings**, so there is no all-time standings query. Championship counts are built from one cached request per season (constructors: about 68 requests the first time `/constructors` is used; `scripts/warm_cache.py` does this ahead of time).
- **Rate limiting:** one request every 0.5 s, and a 429 response is waited out (up to three times) before failing. Jolpica throttled a burst at the documented 4 requests per second during development.
- **OpenF1:** free tier only, for finished sessions (spec 07).
- **Status strings changed in recent seasons.** Jolpica now reports every retirement as "Retired", so the cause of a retirement is unknown from 2024 or so onwards (see spec 03, `/avgpos`).

## Summary

| Module | Service | Auth | Used by |
|---|---|---|---|
| `fastf1_src.py` | FastF1 (F1 live-timing archive) | none | schedule, results, all plots, fastest laps |
| `jolpica.py` | Jolpica (`api.jolpi.ca/ergast/f1`), via `fastf1.ergast.Ergast` | none | standings, constructors, driver, season aggregates, circuit coordinates |
| `wikipedia.py` | Wikipedia REST summary API | none | driver photo |
| `weather.py` | Open-Meteo forecast API | none | schedule weather |
| `fia.py` | fia.com documents pages (HTML) | none | FIA documents (spec 04) |
| `gemini.py` | Google Gemini (`google-genai`) | `GEMINI_API_KEY` | telemetry AI analysis, optional |
| `openf1.py` | OpenF1 | see spec 07 | live session info |

Removed sources: formula1.com (scrape), RapidAPI WeatherAPI, Wikipedia table scrape, YouTube/pytube, `ergast.com`.

## Rules for every source

- **Timeouts:** 10 s connect, 30 s read. One retry on a timeout or 5xx, after 2 s.
- **User-Agent:** `f1buddy/{version} (+{repo url})` on every direct HTTP request.
- **Failure:** raise `SourceError(source_name, detail)`. Never return partial data silently.
- **Fixtures:** every parser has at least one recorded response in `tests/fixtures/{source}/`, and a `-m live` canary that checks the live response still parses.
- **Response cache:** a single SQLite table for small JSON results that are expensive to rebuild.

```sql
CREATE TABLE cache (
  key        TEXT PRIMARY KEY,
  value      TEXT NOT NULL,      -- JSON
  expires_at INTEGER             -- unix seconds; NULL = never
);
```

## FastF1 (`fastf1_src.py`)

- Cache enabled once at start-up at `{DATA_DIR}/fastf1`.
- Functions: `schedule(year)`, `session(year, round, session_name)`, `load(session, laps, telemetry, weather, messages)`.
- Each caller loads only what it needs. Results-only commands load with everything off.
- Lap and telemetry data exist from 2018. Requests for earlier seasons are rejected before any load, by the shared year rule.
- Current API only: `pick_drivers`, `pick_laps`, `fastf1.plotting.get_driver_color(identifier, session)`, `get_team_color(identifier, session)`. No private functions.
- Loads are serialised per (year, round, session) with a lock so two concurrent commands for the same session trigger one download.
- `scripts/warm_cache.py [year]` pre-loads a season (replaces the old `cache.py`).

## Jolpica (`jolpica.py`)

Accessed through `fastf1.ergast.Ergast`, which handles paging, caching and rate limiting. Limits without a token: 4 requests per second, 500 per hour.

| Function | Endpoint | Cache |
|---|---|---|
| `driver_standings(year)` | `{year}/driverstandings` | 1 h current season, forever for past seasons |
| `constructor_standings(year)` | `{year}/constructorstandings` | same |
| `constructors(year)` | `{year}/constructors` | same |
| `constructor_titles()` | `constructorstandings/1` (all seasons) → count per constructor | 24 h |
| `season_results(year)` | `{year}/results`, paged | 1 h current, forever past |
| `season_qualifying(year)` | `{year}/qualifying`, paged | same |
| `races(year)` | `{year}/races` (includes circuit latitude and longitude) | 24 h |
| `all_drivers()` | `drivers`, paged (about 9 requests) | 7 days |
| `driver_career(driver_id)` | see below | 24 h for active drivers, 30 days otherwise |

**`driver_career`** makes these requests and returns one dataclass:

| Stat | Derived from |
|---|---|
| Seasons, championships, points | `drivers/{id}/driverstandings` (one row per season: position and points) |
| Entries, starts, wins, podiums | `drivers/{id}/results`, paged; entries = distinct races, starts = rows with a grid or finishing position |
| Poles | `drivers/{id}/grid/1/results` total |
| Fastest laps | `drivers/{id}/fastest/1/results` total (2004 onwards only) |

The cache matters here: a long career costs about 8 requests against a 500-per-hour limit.

## Wikipedia (`wikipedia.py`)

- Input: the Wikipedia URL that Jolpica returns for a driver.
- `GET https://en.wikipedia.org/api/rest_v1/page/summary/{title}` → `originalimage.source`, falling back to `thumbnail.source`, then to no image.
- Cached 30 days. A failure here returns "no image" and does not raise: the photo is decoration.

## Weather (`weather.py`)

- `GET https://api.open-meteo.com/v1/forecast` with `latitude`, `longitude` (from Jolpica `races`), `daily=temperature_2m_max,temperature_2m_min,precipitation_sum,precipitation_probability_max`, `timezone=auto`, `start_date`, `end_date` (the event's first and last session dates).
- Returns one row per day: date, min and max temperature (°C), precipitation (mm), precipitation probability (%).
- Cached 1 h per event.
- A failure raises `SourceError`; `/schedule` catches it and omits the weather section.

## FIA documents (`fia.py`)

The only HTML scraper. Fully specified in spec 04.

## Gemini (`gemini.py`)

- `google-genai` SDK. Model name from `GEMINI_MODEL` (the default is chosen at implementation time from the models then available, and recorded in `.env.example`).
- One function: `analyse_telemetry(png_bytes, context_text) -> str`.
- If `GEMINI_API_KEY` is unset the module reports itself unavailable and is never called.

## OpenF1 (`openf1.py`)

Specified in spec 07.

## Static lookup tables (`f1buddy/assets/`)

- `countries.json` — country name (as FastF1 and Jolpica spell it) → ISO 3166 alpha-2 code, for flag emojis. Covers every country that has hosted a race, plus aliases such as "Abu Dhabi" → `ae`.
- `nationalities.json` — demonym (as Jolpica spells it) → alpha-2 code, for driver and constructor flags.
- An unknown name gives no flag. A test asserts that every country in the committed schedule fixtures and every nationality in the `all_drivers` fixture resolves.

## Acceptance criteria

1. With the network disabled, the whole test suite passes.
2. Each source parser returns the expected dataclass from its recorded fixture.
3. A 500 response from any source produces `SourceError` after exactly one retry.
4. Two concurrent `session()` loads of the same session perform one FastF1 load.
5. A cached Jolpica result is served without a request until it expires.
6. `pytest -m live` exercises every source once and stays under 60 Jolpica requests.
