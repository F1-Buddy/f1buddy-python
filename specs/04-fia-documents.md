# 04 — FIA documents

`/fiadoc`, the automatic poster, and the admin command that sets where it posts. This is the only feature that scrapes HTML, so the design goal is: when fia.com changes, the breakage is confined to one function, detected within an hour, and fixable by editing that function against a new recorded page.

## Decisions

- **Announcement channel:** unknown until a server exists. Posts are published automatically when the channel is an announcement channel; nothing else changes.
- **Scope of polling:** the landing page only (the most recent event's documents).
- **Page limit:** 20 pages per document, then a link to the PDF.
- **Channel from config:** `FIA_CHANNEL_ID` in the environment sets the channel without running `/setup fia`.

## What the site looks like (checked 2026-10-12)

- Landing page: `https://www.fia.com/documents/championships/fia-formula-one-world-championship-14`. It shows the current season with the latest event's documents expanded.
- Each document is a link whose text contains a title ("Doc 91 - Championship Points") and "Published on DD.MM.YY HH:MM CET".
- PDF paths look like `/system/files/decision-document/2026_singapore_grand_prix_-_championship_points.pdf`. The old bot expected `/sites/default/files/decision-document/`, one reason it stopped working.
- A recalled document appears as an entry with no link.
- Other events are behind links of the form `/decision-document-list/nojs/{id}`.

The landing URL has no season id in it, unlike the per-season URL the old bot hardcoded, so it does not need updating each year.

## Design

```
sources/fia.py
  fetch_listing() -> str                     HTTP only
  parse_listing(html) -> list[FiaDocument]   pure; the only code that knows the page structure
  fetch_pdf(url) -> bytes                    HTTP only
render/fia.py
  render_pages(pdf_bytes, max_pages) -> list[bytes]   PyMuPDF, 150 DPI PNG
cogs/fia.py
  /fiadoc, /setup fia, the polling task
```

```python
@dataclass(frozen=True)
class FiaDocument:
    url: str                      # absolute PDF URL; the document's identity
    title: str                    # "Doc 91 - Championship Points"
    event: str | None             # "Singapore Grand Prix"
    published_at: datetime | None # parsed as Europe/Paris, stored as UTC
```

**`parse_listing` rules.** It deliberately ignores CSS classes and page layout:
1. Take every `<a>` whose `href` ends in `.pdf` and contains `decision-document`.
2. Title: the link's text, with the "Published on …" part removed and whitespace collapsed. If empty, the file name with underscores replaced by spaces.
3. Published time: the first match of `Published on (\d{2}\.\d{2}\.\d{2}) (\d{2}:\d{2})` in the link's text or its parent's text. Absent → `None`.
4. Event: text of the nearest preceding heading-like element. Absent → `None`.
5. Entries with no `href` are skipped.
6. Duplicate URLs are collapsed.
7. Zero documents from a page that was fetched successfully raises `ParseError`. An empty list is never a valid result during a season.

**Ordering.** Newest first by `published_at`; documents without a time keep page order and sort after timed ones.

## Storage

```sql
CREATE TABLE fia_documents (
  url           TEXT PRIMARY KEY,
  title         TEXT NOT NULL,
  event         TEXT,
  published_at  INTEGER,
  first_seen_at INTEGER NOT NULL,
  page_count    INTEGER
);
CREATE TABLE fia_posts (
  url       TEXT NOT NULL,
  guild_id  INTEGER NOT NULL,
  posted_at INTEGER NOT NULL,
  PRIMARY KEY (url, guild_id)
);
```

Rendered pages are cached at `{DATA_DIR}/fia/{sha1(url)}/{page:03}.png`. Zero-padded names keep page order correct when listed. The poster and `/fiadoc` share this cache and these tables.

## Polling task

A `discord.ext.tasks` loop started in the cog's `cog_load`, not in `on_ready`. The body is a plain coroutine `poll_once(now)` so tests call it directly.

**Interval.** 5 minutes from Thursday 00:00 UTC of a race week to Monday 12:00 UTC after it (from the F1 schedule); 30 minutes otherwise.

**Each run.**
1. `fetch_listing` and `parse_listing`.
2. Insert documents not yet in `fia_documents`.
3. **First run** (table was empty before step 2): mark every document as posted for every configured server, and stop. No backlog is posted.
4. For each (document, server with an FIA channel) pair with no `fia_posts` row, oldest document first: render, post, then insert the `fia_posts` row.
5. A row is written only after a successful send, so a failed post is retried on the next run.

**A post.**
- Embed: title = document title (linked to the PDF); description = event and `<t:{published}:f>`; footer "FIA document".
- Pages attached as PNGs, 10 per message. More than 20 pages: the first 20, then a line "Showing 20 of {N} pages. Full document: {url}".
- If the channel is an announcement channel, the first message is published. A publish failure is logged and does not cause a retry of the post.

**Failure handling.**
- Any exception in a run is caught and logged; the loop continues at its normal interval. There is no retry faster than the interval.
- `ParseError`, or 6 consecutive failed runs: send one alert to `OWNER_ALERT_CHANNEL_ID` ("FIA documents: the page no longer parses" / "…unreachable since {time}") and not again for 24 hours. A later successful run sends "FIA documents: working again".
- A document that fails to download or render 3 times is marked posted with a link-only message, so one bad PDF cannot block the queue.
- A server whose channel was deleted or where the bot lacks permission: the failure is logged, the server's FIA channel is cleared after 3 consecutive failures, and other servers are unaffected.

## `/fiadoc`

**Purpose.** Show a recent FIA document on demand.

**Parameters.** `doc` (optional int ≥ 0, default 0): how many documents to go back from the newest. Autocomplete lists the 25 newest as "{title} — {event}" and returns the index.

**Behaviour.**
- Reads from `fia_documents`. If the last successful poll is more than 10 minutes old, it runs one poll first; if that fails, it answers from the stored list and adds "The FIA site couldn't be reached; this may not be the latest."
- Output is the same embed and page attachments as an automatic post. Title "Latest FIA Document" for `doc=0`, the document title otherwise.

**Errors.** `doc` beyond the stored list or negative: `UserError` "Document doesn't exist!". No documents stored and the site unreachable: `SourceError`.

## `/setup fia`

**Purpose.** Choose the channel for automatic posts in this server. Requires the Manage Server permission.

**Parameters.** `channel` (text or announcement channel, optional). Omitted → automatic posts are turned off for this server.

**Behaviour.** Stores the channel in `guild_settings`. When a channel is set, every document currently known is marked as posted for that server, so it receives new documents only. Replies ephemerally with the result, and warns if the bot lacks Send Messages, Attach Files or Embed Links in that channel.

## Acceptance criteria

**Parser**
1. The recorded landing page yields the expected number of documents, each with an absolute `.pdf` URL, a title and a published time.
2. A recalled entry with no link is skipped.
3. A page with the links wrapped in different tags and classes (a hand-edited copy of the fixture) parses to the same documents.
4. A page with no matching links raises `ParseError`.
5. "Published on 11.10.26 17:55 CET" is stored as 2026-10-11 15:55 UTC.

**Polling**
6. First run against an empty database posts nothing and records every document.
7. A later run with two new documents posts both, oldest first, to every configured server.
8. A send failure for one server leaves that pair unposted and retries it on the next run; other servers receive the post once.
9. A 25-page fixture PDF produces two messages of 10 pages and the "Showing 20 of 25" line.
10. `ParseError` sends exactly one alert across three consecutive failing runs, and a "working again" message on recovery.
11. An exception in `poll_once` does not stop the loop and does not shorten the interval.
12. The interval is 5 minutes on the Saturday of a race week and 30 minutes in a week with no race.

**Command**
13. `doc=0` returns the newest stored document; `doc=3` the fourth newest.
14. A second request for the same document reads the cached pages in order (pages 1, 2, … 12, not 1, 10, 11, 12, 2).
15. With the site unreachable and documents stored, the reply includes the stored document and the "couldn't be reached" line.
16. A server that sets its channel after documents exist receives none of them, and receives the next new one.

**Live canary**
17. `pytest -m live` fetches the real landing page and asserts at least one document with a parseable published time.

**Manual**
- Posting and publishing in a real announcement channel.
- Whether fia.com serves the page to the production server's IP (some hosts are blocked by bot protection).

## When the site changes

1. The canary or the owner alert fires.
2. Save the new page as a fixture next to the old one.
3. Edit `parse_listing` until both the new fixture's test and the alternate-markup test pass.

Nothing outside `parse_listing` changes.
