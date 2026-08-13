# cross-cloud-spend-trace

Real-time visibility into exactly which query, job, or pipeline is driving
cloud/warehouse spend — across AWS, Snowflake, and Databricks — before the
invoice arrives.

Built by **Ethan Verduzco** as part of [Cowork OS](../../../..), a portfolio
of projects demonstrating hands-on data-engineering practice against real,
live cloud accounts (not synthetic data).

> **Status: Phases 1-7 done, Phase 8 (QA sign-off) next.** Three source
> collectors, a PySpark analytics core (anomaly detection, month-end
> forecast, optimization suggestions), a full React/FastAPI dashboard, and
> a Learning/Glossary section are all built and verified against real,
> live cloud data — see [`docs/roadmap.md`](docs/roadmap.md) for the full
> phase-by-phase history.

## What this is

**Three independent, Dockerized collectors** — one per cloud/data platform —
each pull real usage/cost data from a live, low-privilege, read-only API
and land it into a shared, Spark-readable raw store:

| Collector | Source | API surface | Cost data |
|---|---|---|---|
| `collectors/aws` | AWS Cost Explorer | `ce:GetCostAndUsage`, `ce:GetCostForecast`, `ce:GetDimensionValues` | Real billed cost (`cost_basis="billed"`) + forecast |
| `collectors/snowflake` | Snowflake `ACCOUNT_USAGE` | `QUERY_HISTORY`, `WAREHOUSE_METERING_HISTORY` views | No dollar cost exposed to a read-only role — lands raw credits/runtime instead |
| `collectors/databricks` | Databricks Jobs/Clusters API | `jobs/runs/list`, `jobs/runs/get`, `clusters/get`, `clusters/events` | No billing API on this trial workspace — lands a clearly-labeled cost *estimate* from runtime × public list-price rates |

Why Databricks doesn't use `system.billing.usage`: Phase 1 confirmed it
directly against Ethan's real trial workspace — the `billing` schema exists
but contains zero tables, and the Account Console's billing API requires a
paid-plan upgrade. See
[`docs/decisions/0002-phase2-raw-store-and-collector-architecture.md`](docs/decisions/0002-phase2-raw-store-and-collector-architecture.md)
for the full reasoning behind every architectural choice in this phase.

**A PySpark analytics core** reads the raw store into one unified
spend-by-source/query/job/model model, then runs three real analyses
against it: leave-one-out z-score anomaly detection (not a hardcoded
dollar threshold — it flagged a real `z=20.90` outlier query in Snowflake's
own history), a run-rate + trend month-end forecast reconciled against
AWS's own native Cost Explorer forecast, and a 4-rule optimization-suggestion
engine that reads real query/job metadata rather than producing templated
text. Full rationale in
[`docs/decisions/0003-phase3-analytics-pipeline-and-databricks-reachability.md`](docs/decisions/0003-phase3-analytics-pipeline-and-databricks-reachability.md).

**A React/FastAPI dashboard** (`frontend/` + `app/`) serves that analytics
output as a real product — Overview, Inputs, Results, Interpretation & Key
Takeaways, Learning, Glossary, Real World, Tools & Technologies, References
& Formulas — built to the identity/component system in
[`docs/decisions/0005-phase4-brand-identity-direction.md`](docs/decisions/0005-phase4-brand-identity-direction.md).
The landing screen opens already populated with this project's own real
ingested data — no "connect your account" step required to see it work.

## Repo layout

```
collectors/
  common/        shared normalized schema, raw-store writer, env-var config
  aws/           Cost Explorer collector (Dockerfile + uv package)
  snowflake/     ACCOUNT_USAGE collector (Dockerfile + uv package)
  databricks/    Jobs API collector (Dockerfile + uv package)
analytics/       PySpark unified model, anomaly/forecast/rules engine
data/raw/        landed Parquet, partitioned by source/table/ingestion date
data/processed/  analytics/'s computed output, read by the API
app/             FastAPI JSON API (serves frontend/dist/ in production)
frontend/        React + Vite + TypeScript + Tailwind + shadcn/ui dashboard
docker-compose.yml
pyproject.toml   uv workspace root (all uv packages above are members)
docs/
  roadmap.md
  decisions/
```

## The raw store

Every collector normalizes its source's native response onto one shared
record shape (`cross_cloud_spend_trace_common.schema.UsageRecord`) and
writes it as Parquet:

```
data/raw/<source>/<table>/ingested_date=YYYY-MM-DD/<table>-<id>.parquet
```

e.g. `data/raw/aws/cost_and_usage/ingested_date=2026-08-12/cost_and_usage-a1b2c3d4.parquet`.

This is deliberately plain, partitioned Parquet rather than a database —
`analytics/`'s PySpark job can read the entire raw store in one call. It
runs locally (`pyspark` local mode), not on live Databricks compute — the
Phase 1 token turned out to be scoped to `jobs`+`clusters` only, with no
`files`/`workspace` access to sync data to a cluster. A self-contained,
ready-to-run Databricks notebook version exists for whenever a
broader-scoped token is issued; see decision 0003 for the full reasoning:

```python
df = spark.read.parquet("data/raw/*/*/*")
```

Partition directories (`ingested_date=...`) follow Spark/Hive's own
`key=value` convention, so `ingested_date` is inferred as a real column
automatically. Source-specific fields that don't map onto the shared schema
are preserved as a `raw_metadata` JSON string column, not discarded.

## Running a collector

### Locally (fastest for development)

```bash
uv sync                      # installs the whole workspace (all 4 packages)
cp .env.example .env         # fill in real credentials — never commit this file
uv run python -m aws_collector
uv run python -m snowflake_collector
uv run python -m databricks_collector
```

### Via Docker (the intended way to run this in anything beyond local dev)

```bash
cp .env.example .env         # fill in real credentials
docker compose build
docker compose run --rm aws-collector
docker compose run --rm snowflake-collector
docker compose run --rm databricks-collector
```

Each collector is a one-shot batch job (it runs one collection pass and
exits), not a long-running server — there's no scheduler wired up yet.

## Running the full app (dashboard)

Backend and frontend run as two processes in development (the frontend's
dev server proxies `/api/*` to the backend):

```bash
# terminal 1
uv run uvicorn app.main:app --reload --port 8000

# terminal 2
cd frontend && npm run dev
```

Open the printed Vite URL (typically `http://localhost:5173`).

**Single-process / production shape**: build the frontend once, then the
backend serves it directly on its own port — same pattern this team's
finance project (`factor-attribution-lens`) established:

```bash
cd frontend && npm install && npm run build && cd ..
uv run uvicorn app.main:app --port 8000
# http://localhost:8000 now serves the full app (API + built UI)
```

## Tests

Every collector has live integration tests (real API calls, no mocking —
this project's own precedent, matching `factor-attribution-lens`'s
`tests/test_api.py`) that skip cleanly when credentials aren't set, rather
than failing the whole suite. `analytics/` and `app/` are tested against
this project's own real, already-ingested data (not synthetic fixtures);
`frontend/` has Vitest coverage including the real anomaly z-score math.

```bash
uv run pytest collectors analytics app   # Python: collectors + analytics + API
cd frontend && npm run test               # frontend: Vitest
```

**On macOS**, if a workspace package import mysteriously fails right after a
clean `uv sync` (`ModuleNotFoundError: No module named 'aws_collector'` etc.),
run `./scripts/fix-macos-venv.sh` first — a real, diagnosed macOS/CPython/`uv`
interaction bug, not a project issue (Docker/Linux is unaffected). Re-run it
after every `uv sync`, since `uv` re-triggers the underlying condition each
time. Full root cause in
[`docs/decisions/0002-phase2-raw-store-and-collector-architecture.md`](docs/decisions/0002-phase2-raw-store-and-collector-architecture.md),
item 9.

## Credentials

Every credential (AWS access key, Snowflake service-user password,
Databricks personal access token) is scoped to a dedicated, least-privilege,
read-only identity created directly by Ethan in each console — see
`docs/roadmap.md`'s Phase 1 entry. No agent has ever seen or generated these
values; they're provided out-of-band and live only in a local, gitignored
`.env` (see `.env.example` for the required variable names). Independently
security-reviewed in Phase 7 — see
[`docs/decisions/0008-phase7-security-review.md`](docs/decisions/0008-phase7-security-review.md)
for the full findings, including confirmation that no credential has ever
touched this repo's git history and a per-source blast-radius fix to
`docker-compose.yml`.

## Tools & technologies

**Data/backend**: Python 3.11, `uv` (workspace-based multi-package
dependency management), `boto3` (AWS Cost Explorer),
`snowflake-connector-python`, `requests` (Databricks REST API), `pydantic`
(schema validation), `pandas` + `pyarrow` (Parquet), PySpark (unified
model, anomaly detection, forecasting), FastAPI (JSON API), Docker (one
image per collector), `pytest` (live integration tests, no mocking).

**Frontend**: React (Vite + TypeScript), Tailwind CSS, shadcn/ui, Recharts
(data visualization), GSAP (the `TracePath` motion component), Vitest.
