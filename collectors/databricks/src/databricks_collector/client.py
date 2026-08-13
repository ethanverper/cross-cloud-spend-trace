"""Thin REST client for the Databricks Jobs/Clusters APIs, authenticated
with a personal access token. Deliberately does not touch `system.billing.usage`
or any Account Console billing endpoint — Phase 1 confirmed both are
unavailable on this trial workspace without a paid upgrade
(`docs/roadmap.md`'s Phase 1 entry).
"""
from __future__ import annotations

import requests

from spend_lens_common.config import require_env

REQUEST_TIMEOUT_SECONDS = 30


class DatabricksClient:
    def __init__(self) -> None:
        self.host = require_env("DATABRICKS_HOST").rstrip("/")
        self._session = requests.Session()
        self._session.headers.update({"Authorization": f"Bearer {require_env('DATABRICKS_TOKEN')}"})

    def get(self, path: str, **params) -> dict:
        response = self._session.get(f"{self.host}{path}", params=params, timeout=REQUEST_TIMEOUT_SECONDS)
        response.raise_for_status()
        return response.json()

    def post(self, path: str, json: dict) -> dict:
        response = self._session.post(f"{self.host}{path}", json=json, timeout=REQUEST_TIMEOUT_SECONDS)
        response.raise_for_status()
        return response.json()
