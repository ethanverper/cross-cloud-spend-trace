# 0002. Phase 2 raw-store shape, collector architecture, and per-source API decisions

Date: 2026-08-12
Status: accepted

## Context

Phase 2 needed to stand up three independent, Dockerized collectors (AWS
Cost Explorer, Snowflake `ACCOUNT_USAGE`, Databricks Jobs API) landing real
usage/billing data into a normalized raw store that Phase 3's PySpark job
(running on Databricks) can read directly. This is a brand-new project with
no established conventions of its own, so several technical calls needed
deciding and recording, per `developer`'s own process.

## Decisions

### 1. Raw store: partitioned Parquet files, not a database

`data/raw/<source>/<table>/ingested_date=YYYY-MM-DD/<table>-<id>.parquet`,
one shared schema (`spend_lens_common.schema.UsageRecord`) across all three
sources. Chosen over a shared Postgres/SQLite instance because:

- Parquet is what Spark reads natively and fastest (`spark.read.parquet`),
  with zero extra dependency (no JDBC driver to install on the Databricks
  cluster side, unlike Postgres).
- The `ingested_date=...` partition directory naming follows Spark/Hive's
  own convention, so the partition column is inferred automatically rather
  than needing a separate metadata table.
- A shared database would need a persistent, always-running service
  (its own Docker container, credentials, network reachability from all
  three collectors) for no benefit Phase 2 actually needs — nothing here
  requires transactional writes or ad hoc SQL against the raw layer itself,
  only "land structured, typed records and be able to bulk-read them later."

**Known gap, explicitly not solved in Phase 2**: files landed under a local
`data/raw/` bind mount are only visible to whatever process runs the
collector containers. Phase 3's PySpark job runs on *actual Databricks
compute* in the cloud, which cannot read a path on Ethan's local machine.
Phase 3 will need an explicit upload/sync step (e.g. to a Databricks Unity
Catalog volume, DBFS, or an S3 location Databricks can read) before its
Spark job can consume this data — Parquet was chosen specifically so that
hop is a `cp`/upload, not a reformat.

### 2. One shared schema across all three sources, not three formats

`UsageRecord` (`collectors/common/src/spend_lens_common/schema.py`) is the
same shape for AWS/Snowflake/Databricks, with `cost_usd`/`cost_basis`
explicitly nullable and provenance-tagged (`"billed"`, `"forecast"`,
`"estimated_list_price"`, or `None`) rather than three different per-source
record shapes. Source-specific fields that don't map onto the shared
columns are preserved in a `raw_metadata` JSON-string column instead of
being dropped — Phase 3 can still reach the original detail per source
without needing three different parsers to do the basic
spend-by-source/date rollup rule 1 of `docs/project-standards.md` will
eventually require.

### 3. uv workspace + per-collector Docker image, not one monolithic image

A root `pyproject.toml` declares a uv workspace with four members
(`collectors/common`, `collectors/aws`, `collectors/snowflake`,
`collectors/databricks`), one shared `uv.lock`. Each collector's Dockerfile
builds from the repo root as context, copies every workspace member's
`pyproject.toml` (uv needs all declared members present to resolve the
workspace even though only one package is synced), runs
`uv sync --frozen --no-dev --package <that-collector>`, then copies in only
`collectors/common/src` and its own `src/` — so each image only ships the
one collector's actual code plus the shared library, not the other two
collectors' source. This satisfies the roadmap's explicit requirement that
each source is its own genuinely Dockerized service (`docs/about-me.md`
point 3 — real, demonstrable Docker experience, not a single shared
container) while still sharing the normalized schema/storage code via a
real dependency (a uv workspace member), not copy-pasted duplication.

### 4. AWS collector — built against exactly the granted IAM surface

The `spend-lens-collector` IAM user has exactly `ce:GetCostAndUsage`,
`ce:GetCostForecast`, `ce:GetDimensionValues` (plus scoped S3/Lambda this
collector never calls). Two concrete consequences:

- **No `sts:GetCallerIdentity` call anywhere** — that action isn't granted,
  so `account_identifier` is left unpopulated for AWS records rather than
  making an API call the IAM policy would reject.
- **Cost Explorer's `TimePeriod.End` is exclusive** and its forecast API
  rejects a `Start` that overlaps already-finalized historical data —
  `collect_cost_forecast` always starts at tomorrow and rolls `End` forward
  an extra month if tomorrow already falls on/after the naive "first of
  next month" boundary (covers running the collector on the last day of a
  month).

### 5. Snowflake collector — lands raw credits/runtime, not a computed dollar cost

`ACCOUNT_USAGE.QUERY_HISTORY` and `WAREHOUSE_METERING_HISTORY` have no
dollar-cost column — Snowflake bills in warehouse credits, and the
credit-to-dollar conversion rate isn't exposed to a read-only role. Rather
than guess a rate, `cost_usd`/`cost_basis` stay `None` for every Snowflake
record; `usage_quantity`/`usage_unit` carry the real native units instead
(query elapsed milliseconds, or warehouse credits). Real per-query dollar
attribution (joining `QUERY_HISTORY`'s execution-time share of a warehouse
against `WAREHOUSE_METERING_HISTORY`'s credit burn, then applying a known
credit price) is a Phase 3 aggregation concern, not a collector concern —
the collector's job is landing the two raw views faithfully.

`ACCOUNT_USAGE` views have documented ~45min-3hr replication latency
(already called out in the roadmap's Phase 1 assumptions) — the collector
and its tests treat a thin/empty result as a valid outcome, not a bug to
retry around.

### 6. Databricks collector — Jobs API cost is an explicit, labeled estimate

Per Phase 1's confirmed finding (`system.billing.usage` has zero tables;
Account Console billing requires a paid upgrade), this collector never
attempts a system-tables or billing-API path. It reads job-run history and
resolves cluster instance type via `cluster_spec`/`cluster_instance` on the
run detail (falling back to a `/api/2.0/clusters/get` lookup when only a
`cluster_id` is present), then applies a small, published-list-price rate
table (`collectors/databricks/src/databricks_collector/pricing.py`) to
runtime × instance type. Every such record is tagged
`cost_basis="estimated_list_price"` with a `pricing_note` string spelling
out exactly how the number was derived — this is a proxy for demonstrating
the attribution mechanism, never presented as (or mistakable for) a real
invoice line. When no cluster/node-type info is available at all (a real
possibility for ephemeral job-scoped clusters or serverless compute on a
trial workspace), `cost_usd`/`cost_basis` are left `None` rather than
guessing — a run record still lands with its real runtime data either way.
`collect_cluster_events` additionally lands raw `/api/2.0/clusters/events`
data (per the roadmap's explicit mention of the cluster-events API) for any
run that did resolve a durable `cluster_id`, as an audit trail Phase 3
could use to build a better estimate later without a collector change.

### 7. Testing: live integration tests, skip-not-fail without credentials

Following `factor-lens/tests/test_api.py`'s precedent (real network calls,
no mocking, since all three source APIs are live/low-privilege/read-only),
every collector's test module is gated with
`pytest.mark.skipif(not os.environ.get(...), ...)` rather than mocking the
API — a missing credential produces a clearly-reported skip, not a false
pass from a mock standing in for the real integration. `collectors/common`'s
raw-store writer is the one piece with a real, credential-free unit test
(Parquet round-trip, partition layout, empty-batch handling) since it has
no external dependency to integration-test against.

### 8. Docker runtime unavailable in this build environment — verified without it, disclosed explicitly

This session's sandbox has no Docker daemon and no arm64-native container
runtime (`brew install colima docker docker-compose` succeeded, but
`colima start` failed — the only Homebrew installed on this machine is the
x86_64 build running under Rosetta at `/usr/local`, and `lima` explicitly
refuses to run nested virtualization under Rosetta emulation on Apple
Silicon). Installing a second, native arm64 Homebrew prefix to work around
this was judged out of scope for a Phase 2 collector task — it's a
system-level toolchain change, not something this phase's assignment
authorized.

**What this means concretely**: every collector's actual Python logic was
verified directly via `uv run` against Ethan's real, live accounts (see
`docs/roadmap.md`'s Phase 2 entry for what came back from each source).
The Dockerfiles/`docker-compose.yml` were written to the same
`ghcr.io/astral-sh/uv:...` multi-stage pattern already proven out in
`factor-lens/Dockerfile`, and reviewed for correctness (workspace member
resolution order, layer caching, entrypoint args), but the actual
`docker compose build && docker compose run` step was **not run in this
session** — Ethan (who has real Docker Desktop / a native runtime on his
own machine) should be the one to run it, which also directly serves his
stated goal for this phase: genuine hands-on Docker experience, not an
agent doing it invisibly on his behalf.

### 9. A real macOS/uv environment bug hit during live verification — diagnosed and worked around

Running any collector locally via `uv run python -m <collector>` failed with
`ModuleNotFoundError: No module named 'aws_collector'` (etc.) even
immediately after a clean `uv sync`. Root cause, confirmed via systematic
debugging (traced through `site.addpackage`'s actual frozen-stdlib source in
the uv-managed CPython 3.11.14 build, not assumed): `uv`'s editable-install
`.pth` files (`_editable_impl_<pkg>.pth`) are written with the macOS `UF_HIDDEN`
filesystem flag set (`ls -lO` shows `hidden`), and CPython 3.11's `site.py`
explicitly skips any `.pth` file with that flag
(`getattr(st, 'st_flags', 0) & stat.UF_HIDDEN` → skip, `site.py` line ~176) —
a real, verified interaction bug between this `uv` Python distribution and
CPython on macOS. **Confirmed Linux-only irrelevant**: `st_flags` doesn't
carry this meaning on Linux, so the Docker images (Linux base image) are not
affected — this is a macOS local-dev-only issue.

Workaround used for this session's live verification:
`chflags nohidden .venv/lib/python3.11/site-packages/_editable_impl_*.pth`
before each run (re-applied after every `uv sync`/`uv run`, since uv
re-hides the files on every sync). Not committed anywhere — it's a
local `.venv` artifact (gitignored) — but worth knowing if a future local
`uv run` mysteriously can't find a workspace package on macOS: this is why,
and the fix is one `chflags` command, not a project/code problem.

### 10. Databricks live verification blocked by a credential/auth-type issue — diagnosed, not a code bug

Running the Databricks collector against the real token in `.env` returned
`401 Unauthorized` from every endpoint tried, including a bare
`GET /api/2.0/clusters/list`. Root-cause investigation before assuming
anything:

- Verified the `Authorization: Bearer <token>` header construction is
  correct (textbook shape, and the same pattern AWS/Snowflake's SDKs use
  successfully against their own APIs the same session).
- Verified `.env` parsing isn't truncating/corrupting the token or host —
  the loaded string lengths match the raw file's line lengths exactly, no
  stray `#`/quote characters.
- Verified `DATABRICKS_HOST` is a well-formed workspace URL (matches the
  `dbc-<id>.cloud.databricks.com` shape, not an account-console URL).
- Made a direct, bypassing-my-own-client request and read Databricks' own
  JSON error body rather than trusting `requests.raise_for_status()`'s
  generic message: `{"error_code":401,"message":"Credential was not sent or
  was of an unsupported type for this API."}`, with
  `x-databricks-reason-phrase` confirming the same text.

This is Databricks' own API telling us the *type* of credential presented
isn't valid for this API surface (a known message pattern for an expired,
revoked, or wrong-kind-of token — e.g. something other than a workspace
personal access token generated via **User Settings → Developer → Access
tokens**, which is what the Phase 1 checklist asked for). This is not
something to guess-fix in code — there's nothing wrong with how the
collector authenticates; the credential itself needs to be re-verified or
regenerated by Ethan. Flagged back rather than attempting speculative
auth-header changes. AWS and Snowflake were both fully verified against
live data in the same session (see `docs/roadmap.md`'s Phase 2 entry) — this
is specifically a Databricks-credential issue, not a systemic problem with
the collector architecture.

## Consequences

- Phase 3's PySpark job needs an explicit upload/sync step before it can
  read this raw store from actual Databricks compute (item 1's known gap)
  — worth scoping into Phase 3's own plan rather than assuming
  `data/raw/` is directly reachable.
- Any real per-query/per-job dollar cost (Snowflake credit pricing,
  Databricks actual billing) still doesn't exist anywhere in this raw
  store — Phase 3's forecast/optimization logic must work with what's
  actually here: real AWS dollars, Snowflake credits/runtime, and a
  labeled Databricks estimate, not three uniformly-priced dollar figures.
- Docker build/run verification is a real, disclosed gap in this phase's
  otherwise-live verification — flagged in the roadmap rather than implied
  as done. Recommended next step: Ethan runs
  `docker compose build && docker compose run --rm <name>` locally for
  each of the three services once credentials are in `.env`.
- Databricks live verification is blocked pending a valid credential (item
  10) — AWS and Snowflake are both fully verified against real data; Phase 2
  is not marked done until Databricks is too. Once Ethan confirms/regenerates
  the personal access token, re-running `uv run python -m databricks_collector`
  (after the macOS `chflags nohidden` workaround in item 9, if run locally
  on this same machine) is the only remaining step.
