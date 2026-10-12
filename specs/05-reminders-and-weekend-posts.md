# 05 — Session reminders and automatic weekend posts

New features. Both run from one background task that watches the schedule.

## Open questions

1. **Reminder scope.** Proposed: both a per-server channel reminder (set by an admin, optionally pinging a role) and personal DM reminders any user can turn on. If you only want one of these, the other can be cut.
2. **Lead time.** Proposed choices: 15, 30 or 60 minutes before a session; default 30.
3. **Weekend post set.** Proposed: a weekend preview on Thursday, the qualifying result, the race result, and a standings update. Sprint results are posted on sprint weekends. Anything to add or remove?

---

## Schedule watcher

One `tasks.loop` running every minute. The body is `tick(now)`, a plain coroutine, so tests drive it with a fake clock.

- It holds the current and next season's `list[Event]` for each series, refreshed every 6 hours, so a rescheduled session is picked up.
- Each tick it works out which reminders and posts are due, sends them, and records each one. Every send is recorded in a table with a primary key covering what was sent and to whom, so a restart or an overlapping tick can never send twice.
- A failure for one recipient is logged and does not stop the others.

---

## Session reminders

**Purpose.** Tell people a session is about to start, with the time shown in their own timezone.

### Commands

**`/remindme`** — personal reminders by DM.

| Parameter | Choices | Default |
|---|---|---|
| `sessions` | All sessions; Qualifying, sprint and race; Race only; Off | required |
| `lead` | 15, 30, 60 minutes | 30 |

Replies ephemerally with what is now set. "Off" removes the subscription.

**`/setup reminders`** — server reminders. Requires Manage Server.

| Parameter | Type | Default |
|---|---|---|
| `channel` | text channel; omitted turns reminders off | |
| `role` | role to mention | none |
| `sessions` | as above, without "Off" | Qualifying, sprint and race |
| `lead` | 15, 30, 60 minutes | 30 |

### Storage

```sql
CREATE TABLE reminder_subscriptions (
  id           INTEGER PRIMARY KEY,
  kind         TEXT NOT NULL CHECK (kind IN ('user','guild')),
  target_id    INTEGER NOT NULL,        -- user id, or guild id
  series       TEXT NOT NULL DEFAULT 'f1',
  sessions     TEXT NOT NULL,           -- 'all' | 'main' | 'race'
  lead_minutes INTEGER NOT NULL,
  UNIQUE (kind, target_id, series)
);
CREATE TABLE reminders_sent (
  subscription_id INTEGER NOT NULL,
  year            INTEGER NOT NULL,
  round           INTEGER NOT NULL,
  session_name    TEXT NOT NULL,
  PRIMARY KEY (subscription_id, year, round, session_name)
);
```

A server's channel and role are in `guild_settings` (`reminder_channel_id`, `reminder_role_id`).

### Behaviour

- A reminder is due when `session start − lead ≤ now < session start` and it hasn't been sent. If the bot was down through the whole window, the reminder is skipped, never sent late.
- Session filter: `all` = every session; `main` = any qualifying, sprint qualifying, sprint, and race; `race` = the race only.
- Message: embed titled "{flag} {EventName} — {SessionName}" with description "Starts <t:{start}:R> (<t:{start}:t>)". Server reminders mention the role, if set, in the message content.
- A DM that fails because the user blocks DMs or shares no server with the bot deletes that subscription.
- A server channel that is missing or not writable 3 times in a row clears that server's reminder channel.
- A session whose time changes after its reminder was sent gets no second reminder.

### Acceptance criteria

1. With a 30-minute lead, ticks at T−31, T−30 and T−29 minutes send exactly one reminder, at T−30.
2. Restarting between two ticks inside the window sends nothing further.
3. A tick first occurring at T+1 sends nothing.
4. A `race` subscription receives nothing for qualifying; a `main` subscription receives qualifying, sprint qualifying, sprint and race on a sprint-weekend fixture and not practice.
5. `/remindme sessions:Off` removes the row and later ticks send nothing.
6. A DM raising `Forbidden` removes the subscription and other recipients still receive theirs.
7. The message uses Discord timestamps built from the UTC start time.
8. `/setup reminders` by a user without Manage Server is refused.

*Manual:* DM delivery and role mention against a real server.

---

## Automatic weekend posts

**Purpose.** Post the weekend's key information to a server channel without anyone asking.

### Command

**`/setup weekend`** — requires Manage Server. `channel` (text or announcement channel; omitted turns the posts off).

### Posts

| Kind | When | Content |
|---|---|---|
| `preview` | Thursday 12:00 UTC of race week | The `/schedule` embed for the event |
| `sprint` | When sprint results are available | Sprint classification, same layout as `/results` |
| `qualifying` | When qualifying results are available | The `/qualifying` embed |
| `race` | When race results are available | The `/results` embed |
| `standings` | When Jolpica standings include this round | Top 10 drivers and all constructors, each with points and position change since the previous round (▲2, ▼1, –) |

**"Results are available"** means: FastF1 returns a results table for the session in which every entry has a classified position or status. The watcher starts checking 30 minutes after the session's scheduled start plus its nominal length (1 h qualifying and sprint, 2 h race), checks every 10 minutes, and gives up after 24 hours.

**Standings** arrive later than results because Jolpica updates some hours after a race. The watcher checks hourly, and posts when the standings' round number equals the event's round. Position change is computed against the standings after the previous round.

### Side effects

The same watcher keeps commands fast:
- After a race result is available: compute and store that round's fastest lap (`/fl` cache).
- On the Monday of race week: generate the circuit image for `/schedule` if it isn't cached.

### Storage

```sql
CREATE TABLE weekend_posts (
  guild_id  INTEGER NOT NULL,
  series    TEXT NOT NULL,
  year      INTEGER NOT NULL,
  round     INTEGER NOT NULL,
  kind      TEXT NOT NULL,
  posted_at INTEGER NOT NULL,
  PRIMARY KEY (guild_id, series, year, round, kind)
);
```

### Behaviour

- Posts reuse the embed functions from spec 02, so the automatic post and the command always match.
- In an announcement channel the post is published.
- A server that enables the feature mid-weekend receives only kinds that become due afterwards.
- A row is written only after a successful send. An unreachable channel is cleared after 3 consecutive failures.

### Acceptance criteria

1. With a fake clock crossing Thursday 12:00 UTC of a race week, one `preview` is sent per configured server, and none in a week without a race.
2. With results unavailable on the first three checks and available on the fourth, exactly one `race` post is sent, after the fourth.
3. A results table with an unclassified entry is treated as not yet available.
4. No post is sent for a session after the 24-hour limit; a warning is logged.
5. `standings` is not sent while Jolpica's latest round is the previous one, and is sent once it matches.
6. Position changes equal the difference between the two rounds' fixtures, including a driver new to the top 10.
7. A sprint-weekend fixture produces a `sprint` post; a conventional weekend produces none.
8. Restarting after any post does not repeat it.
9. A server enabling the feature after qualifying receives `race` and `standings` only.
10. After the `race` post, the round's `/fl` cache entry exists.
