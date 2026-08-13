# spend-lens

Real-time visibility into exactly which query, job, or pipeline is driving
cloud/warehouse spend — across AWS, Snowflake, and Databricks — before the
invoice arrives.

Built by **Ethan Verduzco** as part of [Cowork OS](../../../..), a portfolio
of projects demonstrating hands-on data-engineering practice against real,
live cloud accounts (not synthetic data).

> **Status: Phase 2 — Foundation & Data Integration.** Three source
> collectors exist and land real, normalized usage data into a shared raw
> store. The dashboard, PySpark aggregation/forecast layer, and UI are
> later phases — see [`docs/roadmap.md`](docs/roadmap.md) for the full plan.

## What this is

Three independent, Dockerized collectors — one per cloud/data platform —
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

## Repo layout

```
collectors/
  common/        shared normalized schema, raw-store writer, env-var config
  aws/           Cost Explorer collector (Dockerfile + uv package)
  snowflake/     ACCOUNT_USAGE collector (Dockerfile + uv package)
  databricks/    Jobs API collector (Dockerfile + uv package)
data/raw/        landed Parquet, partitioned by source/table/ingestion date
docker-compose.yml
pyproject.toml   uv workspace root (all four packages above are members)
docs/
  roadmap.md
  decisions/
```

## The raw store

Every collector normalizes its source's native response onto one shared
record shape (`spend_lens_common.schema.UsageRecord`) and writes it as
Parquet:

```
data/raw/<source>/<table>/ingested_date=YYYY-MM-DD/<table>-<id>.parquet
```

e.g. `data/raw/aws/cost_and_usage/ingested_date=2026-08-12/cost_and_usage-a1b2c3d4.parquet`.

This is deliberately plain, partitioned Parquet rather than a database —
Phase 3's PySpark job (running on Databricks) can read the entire raw store
in one call:

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

## Tests

Every collector has live integration tests (real API calls, no mocking —
this project's precedent, matching `factor-lens/tests/test_api.py`) that
skip cleanly when credentials aren't set, rather than failing the whole
suite:

```bash
uv run pytest collectors
```

## Credentials

Every credential (AWS access key, Snowflake service-user password,
Databricks personal access token) is scoped to a dedicated, least-privilege,
read-only identity created directly by Ethan in each console — see
`docs/roadmap.md`'s Phase 1 entry. No agent has ever seen or generated these
values; they're provided out-of-band and live only in a local, gitignored
`.env` (see `.env.example` for the required variable names).

## Tools & technologies

Python 3.11, `uv` (workspace-based multi-package dependency management),
`boto3` (AWS Cost Explorer), `snowflake-connector-python`, `requests`
(Databricks REST API), `pydantic` (schema validation), `pandas` + `pyarrow`
(Parquet), Docker (one image per collector), `pytest` (live integration
tests).
