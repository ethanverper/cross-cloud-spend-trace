# 0003. Phase 3 analytics pipeline: architecture, real-data verification, and the Databricks-reachability decision

Date: 2026-08-12
Status: accepted

## Context

Phase 3 needed PySpark job(s) that read all three sources' raw Parquet
(`data/raw/`, landed in Phase 2) and produce: a unified spend-by-source/
query/job/model view, statistical anomaly detection, a month-end forecast,
and a rules engine generating concrete optimization suggestions from real
ingested metadata. Decision 0002 (item 1) had already flagged, as a known
gap, that Phase 3's PySpark job would need an explicit upload/sync step
before it could read `data/raw/` from actual Databricks compute — this
document resolves that explicitly, rather than silently picking a side.

New code lives in a fourth uv workspace member, `analytics/`
(`spend-lens-analytics`), alongside the three collectors and `common`.

## Decisions

### 1. Explicit PySpark schema over automatic Parquet inference/merge

`analytics/src/spend_lens_analytics/schema.py` defines `RAW_STORE_SCHEMA`,
a fully-nullable `StructType` mirroring `UsageRecord` field-for-field, and
`ingest.read_raw_store()` applies it to every file rather than letting
Spark infer/merge schemas across `data/raw/*/*/*/*.parquet`. Two real,
live-discovered gotchas justify this, both hit reading the actual Phase
1/2 raw store, not hypothetical:

- **All-null columns get inconsistent physical Parquet types across
  files.** Snowflake's `query_history` rows always have `cost_usd=None`
  (decision 0002 item 5); pyarrow doesn't reliably write that as the same
  physical type every time a file happens to be all-null in that column,
  which breaks Spark's `mergeSchema` when it collides with a `double`
  column from another file (e.g. AWS's real nonzero `cost_usd`).
- **The Databricks `job_runs` file's `cost_usd` column was physically
  written as Parquet `INT32`**, not `double`/`null`, even under an
  explicit schema — its one real row has `cost_usd=None` (decision 0002
  item 6, serverless compute exposes no node type to price against).
  Spark's default *vectorized* Parquet reader refuses to widen `INT32` to
  the schema's `double` at read time
  (`SchemaColumnConvertNotSupportedException`); the fix was disabling
  `spark.sql.parquet.enableVectorizedReader`, not special-casing this one
  file (a future partition could hit the same mismatch from any source).

### 2. Anomaly detection: leave-one-out z-score, not a hardcoded dollar amount

`anomaly.detect_anomalies()` scores each row against a **leave-one-out**
baseline — mean/stddev computed from every *other* row in its group, not
including itself — which is what actually lets a genuine outlier register
a high z-score (a naive in-group z-score gets dragged toward its own
outlier). Groups with fewer than `min_group_size` other rows report
`status="insufficient_baseline"` explicitly rather than a fabricated
score; rows with a null value (sources with no cost data at all) report
`status="no_value"`; a zero-variance baseline is handled without a
divide-by-zero.

**Honest verification, per this project's own standard**: the anomaly
mechanism is demonstrably real and firing, not just structurally correct,
at exactly one grain in the current dataset — Snowflake query duration
scored within (warehouse, day):

| query | warehouse | duration | baseline (other queries that day) | leave-one-out z |
|---|---|---|---|---|
| `01c659a4-...0022` — an unfiltered `CUSTOMER JOIN ORDERS ... LIMIT 20` | `SPEND_LENS_WH` | 11,899 ms | mean 260.6 ms, stddev 557.0 ms | **20.90** |
| `01c659a3-...b016` — `CREATE WORKSPACE IF NOT EXISTS ...` | `COMPUTE_WH` | 1,993 ms | mean 167.9 ms, stddev 159.0 ms | **11.48** |

Both are real, genuine statistical outliers in Ethan's actual Query
History data, at `z_threshold=3.0`. Of the other 165 real Snowflake
queries scored: 160 report `status="normal"`, 5 report
`"insufficient_baseline"` (fewer than 5 other same-day, same-warehouse
queries to baseline against).

**Two grains are structural-only, honestly, not because the logic is
wrong**: AWS's real daily S3 cost is genuinely flat
($0.0000046448/day for all 14 observed days — zero variance), so nothing
crosses the threshold there; Databricks has exactly one real job run
landed so far, so its own-history baseline can never be computed
(`insufficient_baseline` for the only row). Both are real, live-verified
*negative* results (`test_real_aws_daily_service_cost_has_no_anomaly_yet`,
`test_real_databricks_has_insufficient_baseline` in
`analytics/tests/test_anomaly.py`), not gaps in the implementation — more
AWS days with real variance, or more Databricks job runs, would let this
same code demonstrate the day/job-level grain too.

### 3. Forecast: independent, uniform run-rate + trend, reconciled (not replaced) with AWS's native forecast

`forecast.month_end_forecast()` computes its own projection the same way
for every source — a simple run-rate (`total-so-far / days-observed *
days-in-month`) and a trend extrapolation (Spark SQL `regr_slope`/
`regr_intercept` fit to cumulative cost vs. day-of-month) — rather than
being AWS-forecast-API-specific. **Why independent, not "just use AWS's
forecast"**: Snowflake and Databricks have no native forecast API at all
(decision 0002 items 5/6) — a source-specific approach would leave two of
three sources with no forecast whatsoever. AWS's own real, already-landed
Cost Explorer forecast record isn't discarded, though:
`reconcile_with_aws_native_forecast()` joins it in alongside our own
number for comparison, never to override it.

**Real result**: AWS's 11 real observed August days (flat
$0.0000046448/day) run-rate-project to **$0.000144** for the month;
because the real series has zero day-to-day variance, the trend method
agrees with run-rate almost exactly there (this is an honest consequence
of genuinely flat data, not a demonstration that trend and run-rate always
agree — `test_trend_diverges_from_run_rate_on_constructed_growth` proves
the two do diverge on a growth pattern, using a constructed series since
the real data has none). AWS's own real native forecast for
2026-08-13→2026-09-01 is **$0.0000511** — lower than our whole-month
run-rate projection, but **not a true apples-to-apples comparison**: the
periods don't match (ours covers the whole month Aug 1–31 from partial
data; Cost Explorer's own forecast covers only the remaining Aug 13→Sep 1
window). At sub-cent dollar amounts this divergence isn't meaningful
either way — surfaced as a real number, not explained away.

**Real, honest negative result**: Snowflake (credits only, `cost_usd`
always null) and Databricks (`cost_usd=None` on its one real run) both
correctly produce **no row** in the dollar forecast — not a fabricated
$0 — confirmed by `test_real_snowflake_and_databricks_have_no_cost_data`.
`native_unit_forecast()` gives Snowflake a real, explicitly-non-dollar
run-rate instead (real credit burn: 0.222666 credits observed on
2026-08-12, projected to ~6.9 credits/month) so that source isn't
forecast-blind entirely, just not in USD.

### 4. Rules engine: only rules groundable in fields the collectors actually land

Four rules, `analytics/src/spend_lens_analytics/rules.py`:

| rule_id | source | quantified? | fired on real data? |
|---|---|---|---|
| `repeated_identical_query` | snowflake | yes (% of time spent on redundant re-runs) | yes — 1 real match |
| `unfiltered_table_scan` | snowflake | no (stated why — no table-distribution data to compute a real %) | yes — 5 real matches |
| `idle_flat_cost_resource` | aws | yes (up to 100% of accumulated cost, conditional on the resource being unneeded) | yes — 1 real match (S3) |
| `databricks_cost_visibility_gap` | databricks | no (it's a visibility gap, not a dollar figure) | yes — 1 real match |

All four fire for real against Ethan's actual ingested data (8 total
suggestion rows) — see `analytics/tests/test_rules.py`. The real, exact
match for `repeated_identical_query`: `SELECT O_ORDERSTATUS, COUNT(*),
AVG(O_TOTALPRICE) FROM SNOWFLAKE_SAMPLE_DATA.TPCH_SF1.ORDERS GROUP BY
O_ORDERSTATUS;` ran 7 times on `SPEND_LENS_WH` (2,527 ms total), flagged
as 86% redundant. The real match for `idle_flat_cost_resource`: Amazon S3
flat at $0.0000046448/day across 14 consecutive days, $0.000065
accumulated.

**Explicit, deliberate gap versus the roadmap's own headline example**
("this Databricks job re-scans the full table every run; partitioning
would cut cost by X%"): that literal rule cannot be implemented against
what this project's Databricks collector is actually able to land. Per
decision 0002 item 6, the Databricks trial workspace exposes no
`system.billing.usage` and the Jobs API carries no query/table/scan-level
metadata anywhere — only cluster/runtime data (job id, run duration, node
type if a provisioned cluster was used). There is no field in
`raw_metadata` that could ever populate a "did this job rescan a full
table" rule; writing it anyway so it silently always returns zero
suggestions would look like coverage that doesn't exist.
`databricks_cost_visibility_gap` is the closest honestly-groundable
substitute: a real Databricks-specific FinOps finding (a cost-attribution
blind spot), evidenced by the run's own real `pricing_note`/duration —
not a stand-in pretending to be the same rule.

### 5. Databricks reachability — resolved with a real, live-tested upload attempt; blocked by a real, diagnosed credential-scope gap

Decision 0002 flagged that Phase 3's PySpark job would need an explicit
upload/sync step before it could read `data/raw/` from real Databricks
compute (local bind-mounted files aren't visible to cloud compute). This
was resolved as a real build-and-test attempt, not a coin flip:

**What was built**: `analytics/src/spend_lens_analytics/databricks_sync.py`,
a DBFS REST client (`create`/`add-block`/`close`, chunked for arbitrary
file size) using the same `DATABRICKS_HOST`/`DATABRICKS_TOKEN`
credentials and client pattern the Phase 2 collector already uses. DBFS
was chosen over a Unity Catalog volume because this trial workspace's UC
status was never confirmed in Phase 1/2, and confirming/enabling it would
be new scope; DBFS is available on every workspace tier with no extra
setup.

**What actually happened when it was run against the real workspace**:
a real, specific `403`: `"Provided access token does not have required
scopes: files"`. Diagnosed before attempting any fix, same standard as
decision 0002's Databricks auth detours — direct follow-up probes in the
same session confirmed this is a **token-wide** scope restriction, not a
DBFS-specific one:

- `GET /api/2.0/workspace/list` → 403, `"...required scopes: workspace"`
- `GET /api/2.1/unity-catalog/catalogs` → 403, `"...required scopes: unity-catalog"`
- `GET /api/2.0/jobs/list` / `GET /api/2.0/clusters/list` → both 200
  (the exact surface Phase 2's collector needed and got scoped for)

The Phase 1/2 `DATABRICKS_TOKEN` is scoped to exactly `jobs`+`clusters` —
sufficient for the Phase 2 collector, insufficient for any file-upload
path Phase 3 needs (DBFS, Workspace import, or Unity Catalog volumes all
require a scope this token doesn't have). This is recorded as a live test
(`analytics/tests/test_databricks_sync.py`,
`test_dbfs_upload_currently_blocked_by_token_scope`), not silently
retried or worked around — it asserts the exact real 403, with a comment
flagging it as the marker to flip once the token scope changes.

**Decision — local execution is this phase's verified primary path,
matching decision 0002's own precedent, not a new one**: every module in
this phase (`unified_model`, `anomaly`, `forecast`, `rules`, `pipeline`)
is genuinely verified today via `pyspark`'s local mode
(`local[*]`/`local[2]`) against the real local `data/raw/` — 28/28 tests
pass, all against real ingested data where real data exists. This is the
same shape of decision as decision 0002 item 8 (Docker build/run verified
only via `uv run` locally, actual `docker compose` execution explicitly
handed to Ethan as the next hands-on step): the code is
real and runs correctly, the specific execution environment (a live
Databricks cluster) is blocked by something only Ethan can fix (issuing a
broader-scoped token), and that blocker is disclosed rather than talked
around.

`analytics/databricks_notebook.py` is a self-contained (zero package-
install dependency — pure `pyspark`/`pyspark.sql.functions`, which ship
on every Databricks Runtime) notebook reimplementing the core mechanism
(unified model, one anomaly check, one forecast, one rule), ready to
`dbutils.widgets` its way through a real run the moment
`sync_raw_store_to_dbfs()` can actually write to the workspace.

**Concrete next step, Ethan's call to make**: generate a new Databricks
personal access token with `files`+`workspace` (and ideally
`unity-catalog`, if this Express-trial workspace supports it) scopes —
or confirm whether this workspace's token-creation UI exposes a scope
selector at all (Phase 1's token was generated via the default flow,
which evidently produced this narrower `jobs`+`clusters` scope). Once
that exists, re-running `sync_raw_store_to_dbfs()` and then
`analytics/databricks_notebook.py` on real Databricks compute is the
literal remaining step to close this gap for real — no code changes
needed on this side.

## Honest data-volume summary — what's real vs. structural-only

| capability | verified against real data? |
|---|---|
| Unified model (all 3 sources) | **yes** — 205 real events, correct per-source/per-day/per-attribution rollups |
| Anomaly detection — Snowflake query duration | **yes, fires for real** — 2 genuine outliers found (z=20.90, z=11.48) |
| Anomaly detection — AWS daily cost, Databricks job cost | structurally correct, exercised against real data, **currently produces an honest negative result** (flat data / single data point) — not yet demonstrated firing |
| Month-end forecast — AWS | **yes** — real $0.000144 run-rate projection from 11 real days, reconciled against AWS's real $0.0000511 native forecast |
| Month-end forecast — Snowflake, Databricks (USD) | structurally correct, **no dollar data exists yet to forecast** (both sources' collectors never populate `cost_usd`) |
| Month-end forecast — Snowflake (native credits) | **yes** — real 0.222666 credits observed, projected |
| Rules engine — all 4 rules | **yes, all 4 fire on real data** (8 suggestion rows) |
| Databricks DBFS upload/sync | **built and live-tested; currently blocked by a real, diagnosed credential-scope gap**, not executed end-to-end on live compute |
| PySpark running *on Databricks compute* specifically | **not yet demonstrated** — local `pyspark` execution is fully verified; the Databricks-hosted run is prepared (`databricks_notebook.py`) and blocked only by the token-scope gap above |

## Consequences

- Phase 3's four analytics capabilities are all real, working code verified
  against Ethan's actual ingested data wherever that data currently has
  enough volume/variance to exercise them — and honestly labeled where it
  doesn't yet.
- The literal "runs on Databricks" requirement from the project's own
  pitch is not yet demonstrated end-to-end; it's one credential-scope fix
  (Ethan's action) away from being demonstrable with the exact code
  already written and locally-verified.
- More AWS days, more Databricks job runs, and any real Snowflake/
  Databricks dollar-cost data (were either source's cost-attribution gap
  from decision 0002 ever closed) would each let a currently-structural
  capability start demonstrating real positive results too — nothing here
  needs new code to prove out, only more time/activity generating real
  usage.
