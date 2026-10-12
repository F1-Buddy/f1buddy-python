# 06 — Predictions game

New feature. Members of a server predict pole and the podium for each race; the bot scores them and keeps a season leaderboard per server.

## Open questions

1. **Scoring.** Proposed below (maximum 25 per race). Change any value you like; they are constants. Because the podium can be predicted with the grid known, podium scores will bunch up; raising the pole value is one way to offset that.
2. **Sprints.** Proposed: Grand Prix only. Sprint predictions would double the commands on sprint weekends for little gain.
3. **Visibility.** Proposed: each part of a prediction is private until that part locks, then everyone's are visible. This stops copying.
4. **Late penalties.** Proposed: scores use the result at the time the race post goes out, and an admin can run a rescore if the classification changes later. The alternative is automatic rescoring whenever the official result changes, which is more moving parts.

## Rules

- One prediction per member, per server, per race. It has two parts, submitted separately:

  | Part | Contents | Locks at |
  |---|---|---|
  | Pole | The pole-sitter | Start of Grand Prix qualifying |
  | Podium | P1, P2, P3 | Start of the Grand Prix |

- Predictions open when the previous race has finished. Each part can be changed any number of times until its own lock, so the podium can be entered after qualifying, up to the race start.
- A member may submit one part and not the other. A part that was never submitted scores 0.
- **Pole** means fastest in qualifying (classified first in the qualifying session), regardless of grid penalties.
- **Podium** is the official race classification when scored.
- On a sprint weekend the locks are still Grand Prix qualifying and the Grand Prix, never a sprint session.

**Scoring**

| Outcome | Points |
|---|---|
| Pole correct | 5 |
| Podium driver in the exact position | 5 each |
| Podium driver predicted, but in a different podium position | 2 each |
| All three podium positions exact | +5 bonus |

Maximum 25. The scoring function is pure: `score(prediction, pole, podium) -> int`, where either part of `prediction` may be missing.

## Commands

**`/predict pole`**

| Parameter | Type | Required |
|---|---|---|
| `driver` | driver | yes |

**`/predict podium`**

| Parameter | Type | Required |
|---|---|---|
| `p1` | driver | yes |
| `p2` | driver | yes |
| `p3` | driver | yes |

Both subcommands:
- Apply to the next race whose part hasn't locked. Between qualifying and the race, `/predict podium` still applies to the current weekend, while `/predict pole` is refused for it.
- Save only their own part and leave the other untouched.
- Driver autocomplete lists the current season's drivers.
- Reply (ephemeral): the race name and the member's full current prediction, with each part shown as its picks or "not set", followed by "locks <t:{lock}:R>" or "locked".

Errors:
- `p1`, `p2`, `p3` not all different → "Pick three different drivers for the podium."
- A driver not in this season → the shared unknown-driver error.
- Pole after qualifying has started → "Pole predictions for {EventName} are locked. You can still predict the podium until the race starts."
- Podium after the race has started → "Predictions for {EventName} are locked. Next up: {next EventName}."
- Used in a DM → "Predictions are per server. Use this in a server."

**`/predictions`**

| Parameter | Type | Default |
|---|---|---|
| `round` | round | the current race weekend if either part is still open or it hasn't been scored; otherwise the next race |
| `user` | member | everyone |

- Each part is shown according to its own lock. Before a part locks, only the caller's own pick for that part is shown; after it locks, every member's pick is shown.
- Between the two locks the reply therefore lists everyone's pole pick, the caller's own podium pick, and the number of members who have entered a podium.
- When any part is still private the reply is ephemeral.
- Once scored, each line shows the points, sorted highest first, with the actual pole and podium at the top.
- More than 25 members: the first 25, then "…and {N} more".

**`/leaderboard`**

| Parameter | Type | Default |
|---|---|---|
| `year` | int | current season |

- Embed "{year} Predictions Leaderboard — {server name}": rank, member, total points, races entered. Top 10, plus the caller's own row if they are outside it.
- Ties share a rank, ordered by number of exact podium hits and then by name.
- No scored predictions yet → "No predictions have been scored yet this season."

**`/predictions-rescore`** — requires Manage Server. `round` (required). Recomputes that round's scores from the current official result and replies with how many scores changed.

## Storage

```sql
CREATE TABLE predictions (
  guild_id   INTEGER NOT NULL,
  user_id    INTEGER NOT NULL,
  series     TEXT NOT NULL DEFAULT 'f1',
  year       INTEGER NOT NULL,
  round      INTEGER NOT NULL,
  pole       TEXT,              -- driver code; NULL = not submitted
  p1         TEXT,
  p2         TEXT,
  p3         TEXT,
  updated_at INTEGER NOT NULL,
  PRIMARY KEY (guild_id, user_id, series, year, round),
  CHECK ((p1 IS NULL) = (p2 IS NULL) AND (p2 IS NULL) = (p3 IS NULL))
);
CREATE TABLE prediction_scores (
  guild_id   INTEGER NOT NULL,
  user_id    INTEGER NOT NULL,
  series     TEXT NOT NULL DEFAULT 'f1',
  year       INTEGER NOT NULL,
  round      INTEGER NOT NULL,
  points     INTEGER NOT NULL,
  exact_hits INTEGER NOT NULL,
  PRIMARY KEY (guild_id, user_id, series, year, round)
);
```

- `/predict pole` writes only `pole`; `/predict podium` writes only `p1`, `p2`, `p3`. Whichever comes first creates the row.
- The leaderboard is a `SUM` over `prediction_scores`. There is no separate totals table.

## Scoring flow

- Scoring is triggered by the schedule watcher (spec 05) at the moment race results become available, for every server with predictions for that round. It does not depend on the server having a weekend channel. Both parts are scored together at that point.
- Scores are written with `INSERT OR REPLACE`, so scoring a round twice gives the same result.
- If the server has a weekend channel, the bot posts "Prediction results — {EventName}": the actual pole and podium, the top 5 scorers for the round, and the season top 5.
- A cancelled race, or one with no classification, is never scored and its predictions are ignored by the leaderboard.

## Acceptance criteria

**Scoring function**
1. All correct → 25.
2. Pole wrong, podium exact → 20.
3. Podium drivers all right but rotated (predicted A-B-C, actual B-C-A) → 6, plus 5 if pole is right.
4. Nothing right → 0.
5. One exact, one misplaced, one absent → 7.
6. A prediction with no pole scores its podium points only; one with no podium scores its pole points only.

**Locks**
7. `/predict pole` one second before qualifying starts is saved; one second after, it is refused with the pole-locked message.
8. `/predict podium` one second after qualifying starts is saved; one second before the race starts it is saved; one second after, it is refused.
9. On a sprint weekend, pole locks at Grand Prix qualifying and the podium at the Grand Prix; neither locks at sprint qualifying or the sprint.

**Commands**
10. `/predict pole` then `/predict podium` leaves one row holding all four values; `/predict podium` alone leaves `pole` empty.
11. Submitting either part twice before its lock keeps the later value and does not change the other part.
12. A duplicate podium driver is refused and nothing is saved.
13. Before the pole lock, `/predictions` shows no other member's picks. Between the locks it shows everyone's pole pick and only the caller's podium pick. After the race starts it shows everything.
14. Predictions in server A do not appear in server B's `/predictions` or `/leaderboard`.
15. `/leaderboard` totals equal the sum of the fixture scores; two members tied on points are ordered by exact hits.
16. A caller ranked 14th sees the top 10 and their own row.

**Flow**
17. When results become available, every prediction for that round gets a score row, in servers with and without a weekend channel.
18. Running scoring twice leaves the same rows and posts the results message once.
19. `/predictions-rescore` after the fixture result is changed updates the affected scores and reports the count; a caller without Manage Server is refused.
