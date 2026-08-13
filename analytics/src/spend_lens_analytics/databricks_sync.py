"""Resolves the real, flagged gap left open at the end of Phase 2
(decision 0002 item 1): `data/raw/` is a local bind-mounted directory on
Ethan's machine — a PySpark job actually running on Databricks compute has
no way to read a path on his laptop. This module is the "explicit upload/
sync step" that gap called for, built against the real DBFS REST API using
the same `DATABRICKS_HOST`/`DATABRICKS_TOKEN` credentials the Phase 2
collector already uses (`spend_lens_common.config.require_env`, same
pattern as `databricks_collector.client.DatabricksClient`).

**Why DBFS and not a Unity Catalog volume**: this trial workspace's actual
UC status was never confirmed in Phase 1/2 — Express-signup trial
workspaces don't reliably provision Unity Catalog by default, and
diagnosing/enabling it would be new scope, not this phase's job. DBFS
(`/api/2.0/dbfs/*`) is confirmed available on every workspace tier
regardless of UC status and needs no extra setup, so it's the safe,
already-verified-reachable target — see docs/decisions/0003 for the full
reachability decision, including why the primary verified path is still
local execution with this upload path proven separately, not a live
cluster run gating this phase's completion.
"""
from __future__ import annotations

import base64
import logging
from pathlib import Path

import requests

from spend_lens_common.config import require_env

REQUEST_TIMEOUT_SECONDS = 60
# DBFS add-block accepts at most 1MB of *base64-encoded* data per call;
# stay comfortably under that with raw (pre-encoding) chunk size.
MAX_CHUNK_BYTES = 700_000

logger = logging.getLogger(__name__)


class DbfsClient:
    def __init__(self) -> None:
        self.host = require_env("DATABRICKS_HOST").rstrip("/")
        self._session = requests.Session()
        self._session.headers.update(
            {"Authorization": f"Bearer {require_env('DATABRICKS_TOKEN')}"}
        )

    def _post(self, path: str, json: dict) -> dict:
        response = self._session.post(f"{self.host}{path}", json=json, timeout=REQUEST_TIMEOUT_SECONDS)
        response.raise_for_status()
        return response.json() if response.content else {}

    def _get(self, path: str, **params) -> dict:
        response = self._session.get(f"{self.host}{path}", params=params, timeout=REQUEST_TIMEOUT_SECONDS)
        response.raise_for_status()
        return response.json()

    def put_file(self, local_path: Path, dbfs_path: str) -> None:
        """Uploads one local file to `dbfs_path`, chunked through DBFS's
        create/add-block/close handle API so it works regardless of file
        size (our Parquet files are small, but the raw store could
        reasonably grow past a single 1MB put)."""
        data = local_path.read_bytes()
        handle = self._post("/api/2.0/dbfs/create", {"path": dbfs_path, "overwrite": True})["handle"]
        try:
            for offset in range(0, len(data), MAX_CHUNK_BYTES):
                chunk = data[offset : offset + MAX_CHUNK_BYTES]
                self._post(
                    "/api/2.0/dbfs/add-block",
                    {"handle": handle, "data": base64.b64encode(chunk).decode("ascii")},
                )
        finally:
            self._post("/api/2.0/dbfs/close", {"handle": handle})

    def list_dir(self, dbfs_path: str) -> list[dict]:
        return self._get("/api/2.0/dbfs/list", path=dbfs_path).get("files", [])

    def mkdirs(self, dbfs_path: str) -> None:
        self._post("/api/2.0/dbfs/mkdirs", {"path": dbfs_path})


def sync_raw_store_to_dbfs(
    local_raw_dir: Path, dbfs_prefix: str = "dbfs:/FileStore/spend_lens/raw"
) -> list[str]:
    """Uploads every `data/raw/<source>/<table>/ingested_date=.../*.parquet`
    file to the same relative path under `dbfs_prefix`, so a Databricks
    notebook can then do exactly
    `spark.read.schema(RAW_STORE_SCHEMA).parquet("dbfs:/FileStore/spend_lens/raw/*/*/*/*.parquet")`
    — the same glob shape `ingest.read_raw_store` already uses locally,
    just rooted at a DBFS path instead of a local filesystem path. Returns
    the list of DBFS paths written, for the caller to log/verify against.
    """
    local_raw_dir = Path(local_raw_dir)
    client = DbfsClient()
    written: list[str] = []
    for local_file in sorted(local_raw_dir.glob("*/*/*/*.parquet")):
        rel = local_file.relative_to(local_raw_dir)
        dbfs_path = f"{dbfs_prefix.rstrip('/')}/{rel.as_posix()}"
        client.put_file(local_file, dbfs_path)
        written.append(dbfs_path)
        logger.info("uploaded %s -> %s (%d bytes)", local_file, dbfs_path, local_file.stat().st_size)
    return written


__all__ = ["DbfsClient", "sync_raw_store_to_dbfs"]
