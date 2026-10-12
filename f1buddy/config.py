import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Config:
    token: str
    admin_ids: frozenset[int]
    data_dir: Path
    alert_channel_id: int | None = None
    fia_channel_id: int | None = None
    gemini_key: str | None = None
    gemini_model: str = "gemini-2.5-flash"
    log_level: str = "INFO"


def _int(env, name):
    value = env.get(name, "").strip()
    return int(value) if value else None


def load(env=os.environ) -> Config:
    missing = [n for n in ("DISCORD_TOKEN", "ADMIN_USER_IDS") if not env.get(n, "").strip()]
    if missing:
        raise SystemExit(f"Missing required environment variable(s): {', '.join(missing)}")
    return Config(
        token=env["DISCORD_TOKEN"].strip(),
        admin_ids=frozenset(int(x) for x in env["ADMIN_USER_IDS"].split(",") if x.strip()),
        data_dir=Path(env.get("DATA_DIR") or "./data"),
        alert_channel_id=_int(env, "OWNER_ALERT_CHANNEL_ID"),
        fia_channel_id=_int(env, "FIA_CHANNEL_ID"),
        gemini_key=env.get("GEMINI_API_KEY", "").strip() or None,
        gemini_model=env.get("GEMINI_MODEL", "").strip() or "gemini-2.5-flash",
        log_level=env.get("LOG_LEVEL", "").strip() or "INFO",
    )
