"""Live integration test against the real Databricks workspace credentials
in `.env` (same skip-if-no-credential pattern as
`collectors/databricks/tests/test_databricks_collect.py`, per decision
0002 item 7 — no mocking of a live, low-privilege, read/write-scoped API).

**This test currently encodes a real, live-diagnosed limitation, not a
success case.** Attempting a real DBFS upload with the Phase 1/2
DATABRICKS_TOKEN returns a real 403: `"Provided access token does not
have required scopes: files"`. Direct, live-diagnosed follow-up checks
(same session) confirmed the token is scoped to exactly `jobs`/`clusters`
— it also gets a real 403 with `"...required scopes: workspace"` on
`/api/2.0/workspace/list` and `"...required scopes: unity-catalog"` on
`/api/2.1/unity-catalog/catalogs`. This is a credential-scope gap, not a
code bug — see docs/decisions/0003 for the full writeup and what unblocks
it (a broader-scoped token, which only Ethan can generate).

If Ethan issues a broader-scoped token and this test starts seeing a real
200/handle back instead, that's the signal to flip this test (and
decision 0003's "known gap" framing) to a real success assertion instead.
"""
from __future__ import annotations

import os

import pytest
import requests

from spend_lens_analytics.databricks_sync import DbfsClient

pytestmark = pytest.mark.skipif(
    not (os.environ.get("DATABRICKS_HOST") and os.environ.get("DATABRICKS_TOKEN")),
    reason="No real Databricks credentials in the environment.",
)


def test_dbfs_upload_currently_blocked_by_token_scope(tmp_path):
    client = DbfsClient()
    probe_file = tmp_path / "probe.txt"
    probe_file.write_text("spend-lens Phase 3 DBFS reachability probe")

    with pytest.raises(requests.exceptions.HTTPError) as exc_info:
        client.put_file(probe_file, "dbfs:/FileStore/spend_lens/_reachability_probe.txt")

    response = exc_info.value.response
    assert response.status_code == 403
    assert "files" in response.json().get("message", "")
