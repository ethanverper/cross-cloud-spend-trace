# cross-cloud-spend-trace — Project Glossary

Every project-specific term explained in this project's Learning section
(`/learning`) and in-app Glossary (`/glossary`), archived here as the source
of truth per `educator`'s standing glossary-maintenance mandate. The live
in-app version (`frontend/src/pages/Glossary.tsx`) is what a visitor to the
deployed dashboard actually sees — this file is the durable record.
Finance-specific terms (alpha, beta, Sharpe ratio, etc.) live in
[Cowork OS's portfolio-wide glossary](../../../../docs/glossary.md) instead,
since they belong to `factor-lens`, not this project.

Every real number below is re-verified directly against
`data/processed/*/run_date=2026-08-12/*.parquet` for decision
[0007](decisions/0007-phase6-learning-and-glossary-content-plan.md), not
transcribed from decision 0003's rounded prose without checking.

Entry format:
```
### <Term>
**Plain language:** ...
**Technical:** ...
**Where it shows up here:** ...
```

## Statistics & Forecasting Methods

### Cost attribution
**Plain language:** Figuring out exactly which query, job, or resource a dollar of spend belongs to — not just which cloud account it landed in.
**Technical:** Joining raw billing/usage records to a resource-level identifier (`attribution_key`/`attribution_kind`) so spend can be grouped and ranked by cause, not just by source-level total.
**Where it shows up here:** `analytics/src/spend_lens_analytics/unified_model.py`'s unified event view; the Results page's "Top spend by service / query / job / warehouse" ranking.

### Leave-one-out z-score
**Plain language:** How many standard deviations a value is from a baseline that was computed without that value's own influence on it — the mechanism this project's anomaly detection is built on.
**Technical:** `z = (x - mean) / stddev`, where mean/stddev are computed from every *other* row in the same group (same day, same warehouse/service), excluding the row being scored. Chosen over a naive in-group z-score because scoring a row against a baseline that includes itself lets a genuine outlier drag the baseline toward it, muting the very signal being measured — and chosen over a hardcoded dollar threshold because a fixed cutoff only works at one order of magnitude (this project's real AWS bill is `$0.0000046/day`; a production account could be six orders of magnitude larger).
**Where it shows up here:** `analytics/src/spend_lens_analytics/anomaly.py`; the real `z=20.90` Snowflake `CUSTOMER JOIN ORDERS` outlier (11,899ms vs. a real baseline of 47 other same-day queries, mean 260.617021ms, stddev 556.965851ms) and the real `z=11.48` `CREATE WORKSPACE` outlier (1,993ms vs. mean 167.929204ms, stddev 159.047481ms, n=113). Frontend implementation: `frontend/src/lib/zscore.ts`, tested against both real numbers in `zscore.test.ts`.

### Anomaly threshold (`z_threshold`)
**Plain language:** How extreme a value needs to be before it counts as a real anomaly, not just ordinary variation.
**Technical:** The `|z| ≥ 3.0` cutoff above which `anomaly.detect_anomalies()` sets `anomaly=True` — a standard "3-sigma" convention balancing false positives against missing genuine spikes. Groups too small to baseline against (`insufficient_baseline`, real: 5 of the 167 real Snowflake queries) or with no value at all (`no_value`) report that status explicitly rather than a fabricated score.
**Where it shows up here:** Every anomaly badge in Results → Anomalies; the interactive `ZScoreExplorer` on Learning.

### Run-rate forecast
**Plain language:** Assume spending stays flat at its average-so-far, and stretch that average out to the end of the month.
**Technical:** `(total_so_far / days_observed) * days_in_month`. Real: AWS's 11 real observed August days (flat `$0.0000046448`/day) run-rate-project to `$0.0001439888` for the month.
**Where it shows up here:** `analytics/src/spend_lens_analytics/forecast.py`'s `month_end_forecast()`; Results → Forecast; Learning's forecast card.

### Trend forecast (`regr_slope` / `regr_intercept`)
**Plain language:** Fit a line to the actual day-to-day trajectory of spend, and extend that line forward instead of just averaging.
**Technical:** Spark SQL's `regr_slope`/`regr_intercept` aggregate functions fit an OLS line to cumulative cost vs. day-of-month, then extrapolate to `days_in_month` — catches growth or decline a flat run-rate average would miss. On the real, zero-variance AWS series, trend and run-rate land on the literal identical `$0.0001439888` (an honest consequence of genuinely flat data). On a constructed, explicitly-labeled growth example (daily cost `$10`→`$28` over 10 days), the two methods genuinely diverge: run-rate projects `$589`, trend projects `$598`.
**Where it shows up here:** Results → Forecast (dashed projection line); the interactive `ForecastMethodCompare` widget on Learning.

### Native-unit forecast
**Plain language:** A forecast in whatever unit a source actually has — like Snowflake credits — instead of a dollar figure, for sources with no cost data.
**Technical:** `native_unit_forecast()` run-rate-projects a source's real non-dollar `usage_unit` rather than fabricating a `$0`. Real: Snowflake's observed 0.222666 credits on 2026-08-12 projects to ~6.9 credits/month.
**Where it shows up here:** Results → Forecast, Snowflake card.

### Optimization suggestion / rules engine
**Plain language:** A specific, evidence-backed recommendation grounded in fields this project's collectors actually landed — not generic cost-savings advice.
**Technical:** 4 rules in `analytics/src/spend_lens_analytics/rules.py`, each reading real `raw_metadata` fields: `repeated_identical_query` (quantified — real: 86% of 2,527ms flagged redundant across 7 identical runs), `unfiltered_table_scan` (not quantified — no row/partition distribution to derive a real % from; 5 real matches), `idle_flat_cost_resource` (quantified — real: up to 100% of a real `$0.000065` accumulated S3 charge, flat across 14 real days), `databricks_cost_visibility_gap` (not quantified — a real visibility gap, not a dollar figure; real job `101154624149862`).
**Where it shows up here:** Results → Optimizations (8 real rows); Learning's rules card (tabbed by rule).

## Cloud / Data Platform Concepts

### AWS Cost Explorer
**Plain language:** AWS's own built-in tool and API for querying historical cost/usage and getting a native month-end forecast.
**Technical:** `ce:GetCostAndUsage`, `ce:GetCostForecast`, `ce:GetDimensionValues` — the exact three read-only Cost Explorer actions this project's IAM policy is scoped to, nothing broader.
**Where it shows up here:** `collectors/aws`; 29 real daily cost-and-usage records + 1 real forecast record (`$0.0000510928` for 2026-08-13→2026-09-01).

### Snowflake `ACCOUNT_USAGE`
**Plain language:** A set of built-in system views Snowflake exposes showing exactly what every warehouse and query actually did and cost, in credits.
**Technical:** `QUERY_HISTORY` and `WAREHOUSE_METERING_HISTORY` views under the shared `SNOWFLAKE` database, reachable via `IMPORTED PRIVILEGES` (not per-schema grants — imported/shared databases reject those, confirmed by a real `SQL compilation error` during Phase 1 setup).
**Where it shows up here:** `collectors/snowflake`; 167 real `QUERY_HISTORY` rows, 4 real `WAREHOUSE_METERING_HISTORY` rows.

### Snowflake virtual warehouse
**Plain language:** The actual compute engine that runs a Snowflake query and burns credits while it's running.
**Technical:** An independently sizeable and suspendable compute cluster — `SPEND_LENS_WH` (X-Small, 60s auto-suspend) is this project's own real dedicated warehouse.
**Where it shows up here:** Every source→warehouse→query `TracePath` breadcrumb in Results and Learning.

### Databricks Jobs API
**Plain language:** The surface this project reads Databricks activity from, since no billing API is available on this trial workspace's tier.
**Technical:** `jobs/runs/list` + `jobs/runs/get` + `clusters/get`/`events` — carries no query/table/scan metadata at all, only cluster/runtime data (job id, duration, node type if provisioned).
**Where it shows up here:** The 1 real job run this project has ingested (`job_id=101154624149862`, `run_id=1043255749606564`, `SUCCESS`, `cluster_source=no_cluster_info_available`).

### DBFS (Databricks File System)
**Plain language:** A place to upload files into a Databricks workspace so cloud compute there can actually read them.
**Technical:** The REST upload surface (`create`/`add-block`/`close`) `analytics/src/spend_lens_analytics/databricks_sync.py` targets — currently blocked by a real, diagnosed `403` token-scope gap (this project's token is scoped to exactly `jobs`+`clusters`, no `files` scope).
**Where it shows up here:** Decision [0003](decisions/0003-phase3-analytics-pipeline-and-databricks-reachability.md), section 5; referenced (not yet reachable from the app's own UI) in the Glossary's DBFS entry.

### FinOps
**Plain language:** The discipline of a company actually knowing and controlling what its cloud/data spend is going toward, instead of just paying whatever the invoice says.
**Technical:** A named, cross-functional practice (engineering + finance) for real-time cost visibility, attribution, forecasting, and optimization of cloud spend at scale — the discipline this whole project is a small, real instance of.
**Where it shows up here:** Real World & Corporate Applications page (real cited 2026 Flexera stat: 29% estimated cloud waste).
