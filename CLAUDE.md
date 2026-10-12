# f1buddy-python

Discord bot serving F1 stats, plots and FIA documents. It is being rewritten from scratch, spec first.

## Where things are

- `specs/` — the source of truth for the rewrite. Read `00-architecture.md` first, then only the spec for the feature being worked on.
- `specs/legacy-inventory.md` — what the old bot does. Use it instead of reading the old code.
- `main.py`, `cogs/`, `repeated/`, `lib/*.py`, `fiadocs*.py`, `cache.py`, `cogsmotogp/` — the old, broken bot. Reference only; nothing here is reused. Don't read it unless the inventory is unclear.
- Assets that carry over: `lib/fonts/`, `botPics/`, `lib/cars/logos/`, `images/`.
- `config.py` and `.env` hold secrets. Never read or commit them.
- `cache/`, `cogs/plots/`, `cogs/fiaDocs/` — generated output; don't search or read them.

## Working efficiently

- Do the work in the main session. Only spawn a subagent when asked, or for a broad search whose file dumps would otherwise fill the context.
- When a subagent is spawned: `haiku` for search and mechanical edits, `sonnet` for implementation, `opus` only for architecture or security review.
- Implement one spec section at a time and make its acceptance criteria pass before moving on.
- Tests must run offline with no Discord token (see `specs/00-architecture.md`, "Testing").
