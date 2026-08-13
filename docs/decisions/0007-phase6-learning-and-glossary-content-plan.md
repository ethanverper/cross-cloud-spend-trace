# 0007. Phase 6 Learning & Glossary: content decomposition plan and real-number grounding

Date: 2026-08-13
Status: accepted

## Context

Phase 6 (`educator`) adds a Learning section and a Glossary to the dashboard
— dual-register (plain language + technical) explanations of the three real
mechanisms Phase 3 actually runs (leave-one-out z-score anomaly detection,
run-rate + trend forecast reconciled with AWS's native forecast, the 4-rule
optimization engine), per `docs/roadmap.md`'s Phase 6 entry.

Per project-standards rule 15, **content ownership determines decomposition
ownership** — `educator` plans this spec before any component is written,
the same discipline decision 0005 section 7 used for Real World / Tools /
References (`brand-creative`-owned) and decision 0006 used for Interpretation
(`business-intelligence`-owned). This document is that plan, written before
`Learning.tsx`/`Glossary.tsx` existed, plus the exact real numbers every
claim below is grounded in (re-verified directly against the actual
`data/processed/*/run_date=2026-08-12/*.parquet` output on disk, not copied
from decision 0003 without checking — see "Real numbers, re-verified" below).

Existing primitives are reused throughout (`Lead`, `Bullets`, `Callout`,
`FootnoteMarker`, `StatHighlight`, `Example`, `TracePath`, shadcn `Accordion`
and `Tabs`) — no new primitive-tier component is introduced. Two small,
content-specific interactive widgets are added (`ZScoreExplorer`,
`ForecastMethodCompare`), scoped the same way `charts/AnomalyCard.tsx` is
scoped: real components built for this project's actual content, composed
from the existing primitives, not a new visual language.

## Real numbers, re-verified against `data/processed/` directly

Pulled fresh via `pandas.read_parquet()` against the real Phase 3 output
(`run_date=2026-08-12`), not transcribed from decision 0003's prose:

- **Headline anomaly**: `01c659a4-...0022`, an unfiltered `CUSTOMER JOIN
  ORDERS ... LIMIT 20` on `SPEND_LENS_WH`, duration `11,899ms`, baseline
  mean `260.617021ms`, stddev `556.965851ms`, `group_n_other=47` (47 other
  real same-day queries), `z_score=20.896044`.
- **Second real anomaly**: `CREATE WORKSPACE IF NOT EXISTS`, `COMPUTE_WH`,
  duration `1,993ms`, baseline mean `167.929204ms`, stddev `159.047481ms`,
  `group_n_other=113`, `z_score=11.475006`.
- **AWS forecast**: `days_observed=11`, `run_rate_per_day=0.0000046448`,
  `trend_slope_per_day=0.0000046448`, `trend_intercept=0.0`,
  `days_in_month=31`, `run_rate_month_end_projection=0.0001439888`,
  `trend_month_end_projection=0.0001439888` (identical to run-rate — a real
  consequence of genuinely zero-variance real data, not a coincidence).
  `aws_native_forecast_usd=0.0000510928`, period `2026-08-13`→`2026-09-01`.
- **`repeated_identical_query`**: `SELECT O_ORDERSTATUS, COUNT(*),
  AVG(O_TOTALPRICE) FROM SNOWFLAKE_SAMPLE_DATA.TPCH_SF1.ORDERS GROUP BY
  O_ORDERSTATUS;` ran 7 times on `SPEND_LENS_WH`, 2,527.0ms total, 361.0ms
  avg/run, **86.0%** flagged redundant (quantified).
- **`unfiltered_table_scan`**: 5 real matches, none quantified (stated why
  in the evidence text itself — no row/partition distribution to derive a
  real % from).
- **`idle_flat_cost_resource`**: Amazon S3 flat at `$0.00000464/day` across
  14 distinct days, `$0.000065` accumulated, up to 100% conditionally
  avoidable (quantified).
- **`databricks_cost_visibility_gap`**: job `101154624149862`, run
  `1043255749606564`, `SUCCESS` in 31s, `cluster_source=no_cluster_info_available`,
  not quantified (it's a visibility gap, not a dollar figure).

These are the only real numbers used anywhere in Learning/Glossary content.
Where a worked example needs a *pattern* the real data doesn't yet exhibit
(forecast trend vs. run-rate genuinely diverging — decision 0003's own
`test_trend_diverges_from_run_rate_on_constructed_growth` exists for exactly
this reason, since the real AWS series has zero variance), a **constructed
series is used and explicitly labeled as constructed**, never presented as
real — same disclosure standard decision 0003 already set.

## Decomposition plan

### Learning page (`/learning`, nav "Learning", eyebrow "08 / Learning")

**Top of page, before the accordion** (sets the "sense of progress" — what's
covered, why it's worth three separate cards, not one wall):
- `Lead`: "Every anomaly, forecast, and suggestion this dashboard shows
  comes from one of three real, documented methods — not a black box, and
  not textbook examples: this page walks through each one using this
  project's own actual results."
- `Bullets` (3 items, one per upcoming card, each naming its real headline
  number) — functions as the syllabus/progress marker before disclosure.

**Progressive disclosure**: a shadcn `Accordion` (`type="single"
collapsible`), one `AccordionItem` per mechanism. Each trigger shows the
mechanism name **plus a live real-number preview** (e.g. `z=20.90`) so
scanning the collapsed list already previews the payoff — matching rule 5's
"clear sense of progress" requirement, not just a bare label list.

**Card 1 — Anomaly Detection (leave-one-out z-score)**
- `Lead`: plain-language one-liner — every value is compared to everything
  else like it, and it isn't allowed to grade its own test.
- `Bullets` (why z-score over a hardcoded dollar threshold, and why
  leave-one-out specifically):
  1. A fixed dollar threshold only works at one order of magnitude — this
     project's real AWS bill is `$0.0000046/day`; a production account
     could be six orders of magnitude larger. One cutoff can't serve both;
     a z-score (standard deviations from a group's own baseline) works
     identically at any scale.
  2. Leave-one-out means the row being scored is excluded from its own
     baseline's mean/stddev — computed once for the whole group, technical
     detail bridging into the `Callout` below.
  3. Groups too small to baseline against (`insufficient_baseline`) or with
     no value at all (`no_value`) report that status explicitly rather than
     a fabricated score — real: 5 of 167 real Snowflake queries hit this.
- `Callout`: the one wrong-mental-model risk — scoring a row against a
  baseline that *includes* itself lets a genuine outlier drag the mean/
  stddev toward it, muting the very signal being measured; that's the actual
  reason leave-one-out was chosen over a naive in-group z-score, not a
  stylistic preference.
- `Example` ("Real worked example"): the real `CUSTOMER JOIN ORDERS` outlier
  rendered as a `TracePath` (snowflake → `SPEND_LENS_WH` → query id →
  `11,899ms` / `z=20.90`), reusing the exact pattern `AnomalyCard` already
  uses elsewhere in the app.
- **Interactive check — `ZScoreExplorer`** (predict-then-reveal, rule 5's
  explicit ask): a slider over a hypothetical query duration, live-computing
  the real leave-one-out z-score formula against the real baseline
  (mean `260.6ms`, stddev `557.0ms`, n=47), with a `StatHighlight` showing
  the live z and whether it crosses `|z| ≥ 3`. A "reveal the real anomaly"
  action snaps the slider to the genuine `11,899ms` value — the reader
  predicts, then sees the real number land far past the threshold.
- `FootnoteMarker`: cross-reference to References & Formulas for the full
  formula block and decision 0003.

**Card 2 — Month-End Forecast (run-rate + trend, reconciled with AWS)**
- `Lead`: two independent ways to project the month's final bill from a
  partial month, computed identically for every source since only AWS has
  its own native forecast.
- `Bullets` (3 items): run-rate in plain words (flat extrapolation of the
  average so far); trend in plain words (fits the actual day-to-day
  trajectory, catches growth run-rate would miss); why *reconciled*, not
  *replaced* — Snowflake/Databricks have no native forecast API at all, so
  a source-specific approach would leave two of three sources blind.
- `Callout`: the real apples-to-apples caveat — AWS's own native forecast
  (`$0.0000511`) covers `2026-08-13`→`2026-09-01` only; our whole-month
  run-rate (`$0.0001440`) covers all of August from partial data. Different
  windows, surfaced side by side anyway, not directly comparable — a reader
  who missed this would wrongly read the gap as a forecast disagreement.
- `Example`: the two real numbers themselves as paired `StatHighlight`s with
  their real period windows labeled.
- **Interactive check — `ForecastMethodCompare`**: a toggle between the
  real AWS series (flat, both methods land on the identical
  `$0.0001439888`) and an explicitly-labeled *constructed* growth example
  (daily cost rising `$10`→`$28` over 10 days — clearly marked as
  constructed, mirroring decision 0003's own precedent for demonstrating
  this exact divergence) where trend (`$598`) and run-rate (`$589`)
  genuinely diverge. Predict-then-reveal: which pattern do you expect the
  two methods to disagree on more?
- `FootnoteMarker`: cross-reference to References & Formulas / decision
  0003.

**Card 3 — Optimization Rules (4 checks against real ingested metadata)**
- `Lead`: four specific checks against fields the collectors actually land
  — not generic "reduce your cloud bill" advice.
- `Callout` (placed first, since skipping it sets up a wrong expectation):
  the roadmap's own headline example ("this Databricks job re-scans the
  full table; partitioning would cut cost by X%") could not be built as
  literally specified — the Databricks Jobs API carries no query/table/scan
  metadata at all on this trial tier, only cluster/runtime data. Named here
  directly so a reader doesn't wonder why that exact rule isn't below.
- A shadcn `Tabs` (reusing the same component `Results.tsx` already uses for
  its own sub-views), one tab per rule, each with an `Example` (the real
  evidence string) and either a `StatHighlight` (the 2 quantified rules —
  86% redundant, up to 100% of the idle S3 charge) or a `Callout` explaining
  *why* the other 2 aren't quantified (stated honestly in the real evidence
  text itself — not a placeholder).

### Glossary page (`/glossary`, nav "Glossary", eyebrow "09 / Glossary")

- `Lead`: every project-specific term this dashboard uses, in both
  registers, cross-referenced to where it's actually computed — plus a
  pointer to the portfolio-wide glossary for terms shared across projects.
- A shadcn `Accordion` (progressive disclosure, consistent with Learning),
  grouped into two categories (Statistics & Forecasting; Cloud/Data
  Platform Concepts), each entry decomposed as: a plain-language line, an
  `Example`-styled "Technical" block (reusing `Example`'s bordered/recessed
  treatment for the more rigorous register rather than inventing a new
  visual form), and a short "where it shows up here" pointer with a real
  in-app link (e.g. to `/results`, `/references`).
- Terms scoped to what's genuinely load-bearing in this project (not every
  Snowflake/AWS/Databricks concept in general): cost attribution,
  leave-one-out z-score, anomaly threshold, run-rate forecast, trend
  forecast, native-unit forecast, optimization suggestion, AWS Cost
  Explorer, Snowflake `ACCOUNT_USAGE`, Snowflake virtual warehouse,
  Databricks Jobs API, DBFS, FinOps.

## Nav / routing changes

`Learning` and `Glossary` inserted after `References` and before `About` in
`nav-config.ts`/`App.tsx` — Learning is the pedagogical companion to the raw
formula reference, Glossary rounds out the content stack before the meta
About/Credits page. `About.tsx`'s eyebrow renumbers `08` → `10` to keep the
sequence consistent (`01` Overview → `10` About).

## Consequences

- `frontend/src/lib/zscore.ts` extracts the leave-one-out z-score formula
  into a small, independently tested pure function
  (`computeLeaveOneOutZScore`), covered by `zscore.test.ts` against the two
  real anomaly numbers above — the same "real numbers, not fixtures"
  testing convention `format.test.ts`/`dedupe-attribution-options.test.ts`
  already established. `ZScoreExplorer` imports this function rather than
  reimplementing the math inline, so the interactive widget and the tested
  formula can't silently drift apart.
- No new primitive-tier component is added to `components/primitives/` —
  `ZScoreExplorer` and `ForecastMethodCompare` live in a new
  `components/learning/` directory, scoped to this content the same way
  `components/charts/` is scoped to Results' charts.
- This plan is implemented verbatim in `Learning.tsx`/`Glossary.tsx` next,
  not improvised during component-writing — the standard this project
  itself flagged as the reason Factor Lens's Interpretation section shipped
  as prose in its first pass.
