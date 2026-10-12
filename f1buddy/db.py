import asyncio
import json
import sqlite3
import threading
import time

# One list of statements per schema version; PRAGMA user_version tracks how many have run.
MIGRATIONS = [
    """
    CREATE TABLE guild_settings (
      guild_id            INTEGER PRIMARY KEY,
      fia_channel_id      INTEGER,
      reminder_channel_id INTEGER,
      reminder_role_id    INTEGER,
      weekend_channel_id  INTEGER
    );
    CREATE TABLE cache (
      key        TEXT PRIMARY KEY,
      value      TEXT NOT NULL,
      expires_at INTEGER
    );
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
    CREATE TABLE reminder_subscriptions (
      id           INTEGER PRIMARY KEY,
      kind         TEXT NOT NULL CHECK (kind IN ('user','guild')),
      target_id    INTEGER NOT NULL,
      series       TEXT NOT NULL DEFAULT 'f1',
      sessions     TEXT NOT NULL,
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
    CREATE TABLE weekend_posts (
      guild_id  INTEGER NOT NULL,
      series    TEXT NOT NULL,
      year      INTEGER NOT NULL,
      round     INTEGER NOT NULL,
      kind      TEXT NOT NULL,
      posted_at INTEGER NOT NULL,
      PRIMARY KEY (guild_id, series, year, round, kind)
    );
    CREATE TABLE predictions (
      guild_id   INTEGER NOT NULL,
      user_id    INTEGER NOT NULL,
      series     TEXT NOT NULL DEFAULT 'f1',
      year       INTEGER NOT NULL,
      round      INTEGER NOT NULL,
      pole       TEXT,
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
    """,
]


class Database:
    def __init__(self, path=":memory:"):
        self._conn = sqlite3.connect(str(path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._lock = threading.Lock()
        version = self._conn.execute("PRAGMA user_version").fetchone()[0]
        for i, script in enumerate(MIGRATIONS[version:], start=version + 1):
            self._conn.executescript(script)
            self._conn.execute(f"PRAGMA user_version = {i}")
        self._conn.commit()

    def execute(self, sql, params=()):
        """Run one statement and return its rows (and commit). Safe from any thread."""
        with self._lock:
            cur = self._conn.execute(sql, params)
            rows = cur.fetchall()
            self._conn.commit()
            self.rowcount = cur.rowcount
            return rows

    async def q(self, sql, *params):
        return await asyncio.to_thread(self.execute, sql, params)

    async def one(self, sql, *params):
        rows = await self.q(sql, *params)
        return rows[0] if rows else None

    # --- small JSON cache -------------------------------------------------
    async def cache_get(self, key):
        row = await self.one("SELECT value, expires_at FROM cache WHERE key = ?", key)
        if row is None or (row["expires_at"] is not None and row["expires_at"] < time.time()):
            return None
        return json.loads(row["value"])

    async def cache_set(self, key, value, ttl=None):
        expires = None if ttl is None else int(time.time() + ttl)
        await self.q("INSERT OR REPLACE INTO cache VALUES (?, ?, ?)", key, json.dumps(value), expires)

    # --- per-server settings ----------------------------------------------
    async def set_setting(self, guild_id, column, value):
        assert column in ("fia_channel_id", "reminder_channel_id", "reminder_role_id", "weekend_channel_id")
        await self.q("INSERT OR IGNORE INTO guild_settings (guild_id) VALUES (?)", guild_id)
        await self.q(f"UPDATE guild_settings SET {column} = ? WHERE guild_id = ?", value, guild_id)

    async def guilds_with(self, column):
        assert column in ("fia_channel_id", "reminder_channel_id", "weekend_channel_id")
        return await self.q(f"SELECT * FROM guild_settings WHERE {column} IS NOT NULL")

    def close(self):
        self._conn.close()
