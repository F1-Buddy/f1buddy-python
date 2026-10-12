# f1buddy-python

Discord bot for Formula 1 (discord.py + FastF1). Rewritten from scratch against the specs in `specs/`.

## Where things are

- `f1buddy/sources/` — one module per external service; the only code that makes network calls.
- `f1buddy/data/` — pure functions returning dataclasses. No Discord types.
- `f1buddy/render/` — dataclasses to embeds (`embeds.py`) or PNG bytes (`plots/`).
- `f1buddy/cogs/` — thin command handlers. `watcher.py` is the one-minute loop behind reminders, weekend posts and prediction scoring.
- `specs/` — behaviour and acceptance criteria per feature. Each spec has a "Decisions" section and, where relevant, "As built: differences from this spec". Read the spec for a feature before changing it.
- `specs/legacy-inventory.md` — what the original bot did. The old code is gone; it's in git history before commit `1c02346`.
- `.env` holds secrets. Never read or commit it.
- `data/` — database and caches; generated, don't read or search it.

## Commands

- Tests (offline, a few seconds): `.venv/Scripts/python -m pytest`
- Canaries against the real services: `.venv/Scripts/python -m pytest -m live`
- Real-data check of commands and plots: `.venv/Scripts/python scripts/smoke.py info` (or `plots`)
- Run the bot: `python -m f1buddy` with the variables from `.env.example` set

## Working here

- Do the work in the main session. Only spawn a subagent when asked, or for a broad search whose file dumps would otherwise fill the context.
- When a subagent is spawned: `haiku` for search and mechanical edits, `sonnet` for implementation, `opus` only for architecture or security review.
- Tests must stay offline: replace sources with `monkeypatch` or the `mock_http` fixture, and fix the clock with the `clock` fixture. `tests/conftest.py` refuses any real network request.
- "Now" comes from `util.now()`; never capture a time at import.
- Jolpica throttles hard (HTTP 429). Keep live experiments small and let the SQLite cache do its job.
