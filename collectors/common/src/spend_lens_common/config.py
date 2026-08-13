"""Environment-variable loading shared by every collector.

Credentials never live in code or in git — each collector reads them from
process environment variables, populated either by a local, gitignored
`.env` file (via `python-dotenv`, for local/dev runs) or by Docker Compose's
`env_file:`/`environment:` at container start. No collector logs a
credential value; `require_env` raises on a missing variable rather than
letting a collector silently run unauthenticated.
"""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


def require_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(
            f"Missing required environment variable: {name}. "
            "Set it in your local .env file (see .env.example) or in the "
            "environment the collector's container is started with."
        )
    return value


def raw_data_dir() -> Path:
    """Where landed parquet files go. Defaults to `./data/raw` for local
    (non-Docker) runs; Docker Compose overrides this to the bind-mounted
    `/data/raw` inside each collector's container."""
    path = Path(os.environ.get("RAW_DATA_DIR", "./data/raw"))
    path.mkdir(parents=True, exist_ok=True)
    return path
