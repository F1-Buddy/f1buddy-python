# 07 — Live session info

New feature, and the least certain one: it depends on a live data source, and the free options are limited. **A decision is needed from you before this is built** (question 1).

## Open questions

1. **Which live source?**

   | Option | Cost | What I know |
   |---|---|---|
   | **A. OpenF1 paid tier** (recommended if you want live data) | €9.90 per month | Documented REST, MQTT and WebSocket access to live data, about 3 seconds behind the track. Needs an account; 6 requests per second and 60 per minute. |
   | **B. F1's own live-timing feed**, read with FastF1's live-timing client | Free | Undocumented and unsupported by F1. I have not confirmed that it is currently reachable without an F1 account, or that reading it in real time is within its terms. Needs a short test during a real session before any commitment. |
   | **C. Post-session only** | Free | Drop "live". OpenF1's free tier and FastF1 both provide weather, track status and race control messages after a session ends. `/live` becomes a session recap. |

   The spec below is written against a small interface so A or B can be swapped without touching the commands. With no source configured, the feature degrades to C on its own.

2. **Channel feed.** Proposed: optional per-server channel that receives race control messages as they happen (flags, safety car, penalties). This can be busy: a race produces 50 to 100 messages. Batching is specified below. Want it, or only the on-demand `/live` command?

## Source interface

```python
class LiveSource(Protocol):
    available: bool
    async def current_session(self) -> LiveSession | None
    async def weather(self, session_key) -> Weather | None
    async def track_status(self, session_key) -> TrackStatus
    async def race_control(self, session_key, since: datetime | None) -> list[RaceControlMessage]
    async def order(self, session_key) -> list[OrderRow]      # position, driver, gap to leader, tyre
```

- `sources/openf1.py` implements it against OpenF1 (`sessions`, `weather`, `race_control`, `position`, `intervals`, `stints`).
- With `OPENF1_USERNAME` and `OPENF1_PASSWORD` set, it requests an access token and uses the live endpoints. Without them, `available` is false during a session and the same endpoints are used for finished sessions only (free tier, 3 requests per second and 30 per minute, data from 2023).
- Polling (option A): every 10 seconds while a session is running and at least one server has a live channel or a `/live` request was made in the last 5 minutes; otherwise no requests are made. This is 6 calls per poll cycle at most, inside the paid limit.

## `/live`

**Purpose.** A snapshot of the session that is running now, or the most recent one.

**Parameters.** None.

**Output.**
- Title "{flag} {EventName} — {SessionName}" and a status line: "Live · lap {n}/{total}", "Finished <t:{end}:R>", or "Starts <t:{start}:R>".
- "Track": 🟢 Green, 🟡 Yellow (with sector if known), 🟠 VSC, 🚗 Safety Car, 🔴 Red flag, 🏁 Chequered.
- "Weather": air and track temperature, humidity, wind speed and direction, "Rain" yes/no.
- "Order": top 10, as position, team emoji, driver code, gap to leader, current tyre.
- "Race control": the 5 most recent messages with their time (`<t:…:T>`).
- Footer: "Live data is about {n} seconds behind" when live; "Final" otherwise.

**Behaviour.**
- A session is running and the source is live-capable → live snapshot.
- A session is running and no live source is configured → the schedule line plus "Live data isn't enabled on this bot. A recap will be available after the session."
- No session running → recap of the most recent finished session (from 2023 onwards), plus when the next one starts.
- Snapshots are cached for 10 seconds, so many users calling `/live` at once cost one poll.

## Live channel feed (if wanted)

**`/setup live`** — requires Manage Server. `channel` (omitted turns it off). Adds `live_channel_id` to `guild_settings`. Only works when a live source is configured; otherwise the command says so.

**Posts during a session**
- Session start: "🟢 {SessionName} is under way".
- Track status changes: yellow, VSC, safety car, red flag, restart, chequered flag.
- Race control messages in the categories penalty, investigation, and incident. Blue flags, track-limit deletions and DRS messages are left out.
- Session end: final top 10 (the full result follows from the weekend post, spec 05).

**Batching.** Messages are collected and sent as one embed at most once every 30 seconds per server, oldest first, up to 10 lines; a red flag or safety car is sent immediately. This keeps the bot inside Discord's rate limits and the channel readable.

**De-duplication.** Each race control message is identified by (session, timestamp, text). The last message sent per server and session is stored in the `cache` table, so a restart mid-session resumes without repeating.

## Acceptance criteria

All use a fake `LiveSource` fed from recorded OpenF1 responses for one race.

1. With a live session in the fake source, `/live` shows the track status, weather, ten order rows and five race control messages from the fixture.
2. With `available = False` during a session, `/live` returns the "isn't enabled" reply and makes no live request.
3. With no session running, `/live` shows the recap of the last finished session and the next session's start.
4. Ten `/live` calls within 10 seconds cause one set of source calls.
5. With no live channel configured anywhere and no recent `/live`, a running session causes no polling.
6. Feed: a fixture sequence green → yellow → safety car → green produces posts in that order, with the safety car sent immediately and the others within one batch interval.
7. Feed: blue-flag and track-limit messages are never posted.
8. Feed: 30 messages arriving within 30 seconds result in at most two sends, each with at most 10 lines, and the remainder in the following batch.
9. Feed: restarting mid-session does not repost earlier messages.
10. A source error during a session is logged, the next poll proceeds, and `/live` reports "Live data is temporarily unavailable."

*Manual, and required before release:* run through one real session to confirm the delay, the request volume and the message filtering.

## Recommendation

Build this last. Specs 02 to 06 don't depend on it, and question 1 can be answered after the rest of the bot is running. If the answer is C, `/live` and its acceptance criteria 2, 3 and 4 are the whole feature.
