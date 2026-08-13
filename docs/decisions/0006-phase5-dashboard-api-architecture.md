# 0006. Phase 5 dashboard: API architecture, real bugs found and fixed, and honest verification

Date: 2026-08-13
Status: accepted

## Context

Phase 4 (decision 0005) set the full brand/identity spec for the dashboard
but explicitly left one thing undecided: this project has no frontend and
no API layer yet, only Python scripts/PySpark jobs (`collectors/`,
`analytics/`). Phase 5's job (`business-intelligence`) is to build the
actual React dashboard against that spec **and** decide how it gets real
data — a call decision 0005 deliberately left open ("no architecture
tradeoff is being forced by this direction... [but] Phase 5 scopes it as a
real component, not an afterthought").

## Decision 1 — API layer: read Phase 3's cached Parquet output with pandas, don't re-run PySpark per request

A new uv workspace member, `cross-cloud-spend-trace-api` (root
`pyproject.toml` is now also a package, alongside the existing five
members), with `app/main.py` (FastAPI app + production static-asset
serving) and `app/api/routes.py` (the JSON contract), following the
structural pattern already established by
`factor-attribution-lens/app/main.py` and `app/api/routes.py` — a pure
JSON API in dev, one deployable service in production (frontend's
`dist/` mounted via `StaticFiles`, SPA fallback route registered last).

**Why reading cached output, not re-running the pipeline**: `analytics/`'s
PySpark pipeline (decision 0003) is real and correct, but spinning up a
local Spark session (`local[*]`, a JVM) per HTTP request would be slow and
heavy for a request/response API, and would recompute results that don't
actually change between requests — the raw store only grows when a
collector is re-run, and the processed output only changes when
`python -m cross_cloud_spend_trace_analytics.pipeline` is re-run. `app/data/loader.py`
reads the same `data/processed/*/run_date=.../part-*.parquet` files the
pipeline already wrote, plus every partition under `data/raw/` for real
record counts, once at process start via pandas/pyarrow, and holds them in
memory (`functools.lru_cache`).

**Why this is still real, not a shortcut that fakes data**: every number
the API serves is the literal output of a real PySpark run against
Ethan's real ingested data — decision 0003's own numbers (z=20.90, the
$0.0001439888 AWS run-rate projection, 8 optimization suggestions) are
exactly what `GET /api/overview`/`/api/anomalies`/`/api/forecast`/
`/api/optimizations` serve, verified byte-for-byte against the source
Parquet during this phase's own testing (`app/tests/test_api.py`, 11/11
passing, asserting the real numbers directly, no mocking/fixtures).

**Consequence, disclosed**: if Ethan re-runs a collector or the pipeline,
this API process needs a restart (or a call to `loader.reload_store()`) to
pick up the new `run_date=`/`ingested_date=` partition — there's no
file-watcher. Acceptable for this project's actual update cadence (a
manual pipeline re-run, not a live streaming system), and cheap to add
later if that changes.

**Constrained-input enforcement, defense in depth (rule 2)**: `source` and
`attribution_kind` query params are validated server-side against the real
known values (`VALID_SOURCES` derived from `app/data/constants.py`) — an
unrecognized value 400s before it can shape a pandas filter, matching
`factor-attribution-lens`'s own ticker-validation pattern.

## Decision 2 — frontend stack and shadcn style, with one real gotcha

React + Vite + TypeScript + Tailwind CSS v4 + shadcn/ui per rule 4,
`recharts` for every chart, GSAP for the `TracePath` connector-draw
animation, exactly as decision 0005 anticipated. One real, live-hit
implementation gotcha: `shadcn init`'s current default style
(`base-nova`) is built on `@base-ui/react` instead of Radix, and its
`Button`/`Popover` primitives don't support the `asChild`+`Slot`
composition pattern used throughout this codebase (`<Button asChild><Link
.../></Button>`) — every such usage failed to typecheck. Fixed by
re-initializing with `-b radix` (the `radix-nova` style), which uses real
Radix primitives (`Slot`, actual `asChild` support) — no code written
against the wrong style was salvageable, so the component set was
regenerated rather than patched.

Fonts are self-hosted via `@fontsource-variable/geist` and
`@fontsource-variable/geist-mono` (real npm packages, not a CDN `<link>`)
so the app has no external font dependency at runtime, matching this
identity's own emphasis on precision/no external trust dependency.

## Real bugs found during live verification, and fixed

Per this project's own standard (verify live, don't just confirm the
build compiles), the dashboard was actually run (`uv run uvicorn
app.main:app` + `npm run dev`) and driven via the Browser tools, in both
dark and light mode and at a mobile viewport. Three real bugs surfaced
this way, none of which a type-check or a "did it render" check would
have caught:

1. **`StatHighlight`'s count-up animation truncated sub-cent dollar
   figures to `$0`.** The animated tick handler rounded to 3 decimal
   places every frame (`Math.round(n * eased * 1000) / 1000`); AWS's real
   $0.0001439888 month-end projection rounds to `0` at 3 decimals, so the
   landing screen's forecast stat tile visibly showed `$0` for its entire
   count-up, settling on a truncated value. Live-caught via a screenshot
   during verification. Fixed by giving `StatHighlight` a `format`
   callback prop (`formatUsd`/`formatNumber`) instead of a hardcoded
   round, and adding `frontend/src/lib/format.test.ts` (Vitest) asserting
   the real value round-trips at full precision — this test failed
   against the *first* fix attempt too (a `formatUsd` default of 7
   decimals still truncated the real $0.0000046448 AWS daily figure),
   caught before it shipped, not after.
2. **`TracePath` nodes overlapped illegibly at a 375px mobile viewport.**
   The original layout gave every non-final node `flex: 1 1 0%`, letting
   flex-shrink compress node content into each other rather than
   truncating cleanly, and the connector line was `flex-1` too — visually
   confirmed via a real mobile-viewport screenshot (node labels rendering
   on top of each other, not just wrapping). Fixed by making every node
   `shrink-0` (fixed content width, real `truncate` behavior) and every
   connector a fixed width (`w-8 md:w-12`, not `flex-1`), with the whole
   row wrapped in `overflow-x-auto` — on a narrow viewport the breadcrumb
   now scrolls horizontally instead of compressing into unreadable text,
   verified with a follow-up screenshot showing clean, non-overlapping
   nodes.
3. **A real duplicate-React-key warning in the Inputs page's job/query
   dropdown**, caught via `read_console_messages` during live
   verification, not a visual glitch. Root cause, confirmed against the
   real API response: a small number of real Snowflake rows share the
   same `attribution_key` across two different `attribution_kind` values
   (a `query`-kind row that fell back to its warehouse name as its key
   when no per-query id/cost existed at that grain) — `GET /api/filters`
   genuinely returns `(snowflake, query, SPEND_LENS_WH)` and
   `(snowflake, warehouse, SPEND_LENS_WH)` as two distinct rows. Since the
   Inputs page's filter state only carries a single `attributionKey` (not
   kind), rendering both as separate `<SelectItem>`s with the same
   `value` was both a React-key bug and a UX ambiguity. Fixed by
   extracting `dedupeAttributionOptions()` into
   `frontend/src/lib/dedupe-attribution-options.ts`, covered by three
   Vitest cases using the real duplicate-key shape, not a synthetic one.

None of these three bugs were hypothetical or style nitpicks — all three
were confirmed live, in the actual rendered app, against real data, before
being called fixed.

## Consequences

- `app/`, `frontend/`, and this phase's real bug fixes are committed in
  three separate, real, incrementally-pushed commits (API layer;
  scaffold + identity system; full section set) rather than one combined
  drop, per Ethan's own standing request for visible incremental progress
  on this repo.
- `data/raw/` and `data/processed/` remain gitignored (only `.gitkeep`
  tracked, an existing Phase 2/3 convention this decision doesn't change)
  — this API layer depends on those directories being populated locally
  by running the collectors/pipeline. Phase 10's eventual deploy will need
  either a real pipeline run against real credentials on the deploy target,
  or a deliberate decision to ship a committed data snapshot — flagged
  here for `devops` to pick up explicitly, not assumed away.
- 11 backend tests (`app/tests/test_api.py`) and 13 frontend tests
  (`frontend/src/lib/*.test.ts`) pass, all against this project's real
  numbers, not synthetic fixtures.
