# Phase 8 — QA Verification & Sign-off

Date: 2026-08-13
Tester: `qa-tester`
Scope: full, independent first QA pass on `cross-cloud-spend-trace` against this project's own "Definition of done (v1)" (`docs/roadmap.md`) and `docs/project-standards.md`, on `main` (commit `d63cad0`, working tree clean throughout — no application code touched by this pass).

## Verdict: READY (four non-blocking findings, no blockers)

All four items found in this pass are minor/moderate UI-consistency or environment-documentation issues, not violations of the definition of done. Every core capability (real three-source ingestion, cost attribution, anomaly detection, month-end forecast, optimization suggestions, all required sections, the credential-isolation architecture) is real, live-verified against real data, and holds under edge cases. Recommend proceeding to Phase 9/10; the four items below should go back to `developer` as quick follow-ups but should not hold up publishing/deploy.

## What was covered

### Automated regression
- **Backend**: `uv run pytest collectors analytics app` — **50/50 passing**, all against real, live, non-mocked data (11 collector tests including 3 live AWS/Snowflake/Databricks integration tests that actually re-authenticated against the real accounts today; 28 analytics tests; 11 API tests). One environment note: this failed to even collect on a fresh `uv sync` on this machine, reproducing the exact macOS `UF_HIDDEN`/`.pth`-file bug decision 0002 already documented — fixed with the same documented workaround (`chflags nohidden .venv/lib/python3.11/site-packages/*.pth`). Not a code bug (Linux/Docker unaffected, already disclosed), but this workaround isn't captured anywhere runnable yet — see Finding 4.
- **Frontend**: `npm run test` (Vitest) — **18/18 passing**. `npx tsc -b` — clean, zero errors. `npm run build` — clean (one pre-existing, expected warning: main JS chunk >500kB, not a regression, no code-splitting was ever in scope). `npm run lint` (oxlint) — 0 errors, 8 pre-existing advisory `react-refresh`/`exhaustive-deps` warnings common to this stack, non-blocking.

### Independent confirmation of Phase 7's central architecture claim
Decision 0008 concluded `app/` never touches a live cloud credential at request time, verified by reading the code. This pass verified it independently, at runtime: `.env` was moved out of the project directory entirely (not just unset), the FastAPI backend was started fresh, and `GET /api/overview` still returned the complete real dataset (29 AWS / 167 Snowflake / 1 Databricks records, the real z=20.90 anomaly, the real $0.0001439888 forecast) with zero errors. `.env` was restored immediately after and its contents were never printed to any tool output (per decision 0008's own incident, this check was done deliberately via `mv`/`curl`, never `docker compose config` or anything else that interpolates `.env`). **Confirmed: the dashboard genuinely needs zero live credentials to run.**

One related, non-blocking flag: the backend's own live-credential integration tests (`collectors/*/tests`) successfully re-authenticated against the real AWS/Snowflake/Databricks accounts today, which means **decision 0008's recommended credential rotation (AWS access key, Databricks token, Snowflake password) has not yet happened**. This doesn't block Phase 8 — same conclusion decision 0008 itself reached — but it's worth re-flagging to Ethan since it's now been open since Phase 7.

### Method note — browser tooling
The in-app Browser pane's coordinate/ref-based clicks were unreliable for this specific app's Radix `Tabs`/`Select` components in this session (clicks reproducibly landed inside adjacent `recharts` chart areas instead of the intended tab/option, with no visible state change). Switched to the `webapp-testing` skill's Playwright harness (headless Chromium, both desktop 1280px and mobile 375px viewports) for all interactive verification below, and used the Browser pane for the initial screenshots that didn't require clicking. This is recorded as a tooling note, not an app defect — Playwright confirmed every interaction below works correctly and with zero console errors.

### All required sections driven live, with real data
Verified via Playwright (`page.goto` + `wait_for_load_state("networkidle")` + `inner_text()`/screenshots), not inferred from source:

- **Overview** (rule 14): opens already populated with real data, no connect-account gate. One-sentence mechanism statement, three source-record chips, four concept cards, a real z=20.90 anomaly `TracePath` card, and a real forecast stat + chart — all visible without scrolling at 1280px. Confirmed reachable with zero live credentials present (see above).
- **Inputs** (rule 2): source and job/query fields are real Radix comboboxes populated from `GET /api/filters` (confirmed via captured network request — 15 real options across 3 sources), not free text. Date fields are native `type="date"` inputs. The page explicitly cites where the option list comes from and its known limitation (rule 7): *"Databricks currently has exactly one real job run landed, so its own option list is correspondingly thin; that's the real state of the data, not a loading bug."* Server-side validation independently confirmed (defense in depth): `GET /api/spend?source=azure` → `400`; `GET /api/spend?start=not-a-date` → `400`; an adversarial `<script>alert(1)</script>` source value → `400`, safely rejected (JSON response type, no reflected-XSS surface).
- **Results** (rule 6): all four tabs (Spend / Anomalies / Forecast / Optimizations) render real `recharts` visuals plus real numbers matching decision 0003's own values (z=20.90 and z=11.48 anomalies, $0.0001439888 AWS run-rate vs. $0.0000510928 AWS native forecast, 8 optimization suggestions / 1.968 quantified savings units). `TracePath` renders correctly on both desktop and 375px mobile — the Phase 6 mobile-overlap fix holds (nodes truncate cleanly, horizontal scroll, no overlap).
- **Interpretation & Key Takeaways** (rules 9a/15) — see "Rule-15 spot-check" below, this is the headline result of this pass.
- **Learning**: both named interactive widgets were actually operated, not just read from source. `ZScoreExplorer`'s range slider live-recomputes the real leave-one-out z-score formula (manually set to 6000ms → live z-score updated to 10.30, hand-verified against `(6000 − 260.617) / 556.966 ≈ 10.30`); its "Reveal the real anomaly" action correctly jumps to the real 11,899ms/z=20.90 value and surfaces a confirming `Callout`. `ForecastMethodCompare`'s "Real AWS data" / "Constructed growth" toggle correctly switches between the real flat AWS series (both run-rate and trend methods land on the identical $0.0001439888) and an explicitly labeled **"CONSTRUCTED EXAMPLE — NOT REAL DATA"** $589-vs-$598 growth scenario — never blurring the two.
- **Glossary, Real World, References & Formulas, Tools & Technologies, About & Credits** — all read live, all decomposed into bullets/callouts/stat-highlights/worked examples on spot-check, no wall-of-prose section found, including at 375px mobile (Optimization Rules' nested `Tabs` inside Learning also confirmed non-clipped on mobile — the Phase 6 fix holds there too).

### Rule-16 entity grep
`grep -rnoE "&[a-z]+;" frontend/src --include="*.ts" --include="*.tsx"` (excluding `dangerouslySetInnerHTML` lines) found exactly **one** match: `&gt;=` in `frontend/src/pages/ReferencesFormulas.tsx:115`, inside plain JSX text (not a `data/*.ts` string interpolated via `{variable}`). Confirmed via rendered `get_page_text()` output that this renders correctly as `>=` — JSX text nodes decode named HTML entities at compile time, unlike a JS string variable interpolated into JSX, so this is **not** a live instance of the rule-16 bug class. This project doesn't use a `data/*.ts` content-file pattern the way Factor Lens does (content is authored inline in page/component `.tsx` files), so the grep was run against all page/component source as the closest equivalent. See Finding 3 for the one cosmetic cleanup recommendation anyway.

### Interpretation & Key Takeaways / advice-language grep (rule 9a hard limit)
`grep -rinE "you should|consider (re)?balanc|\bbuy\b|\bsell\b|recommended" frontend/src --include="*.tsx" --include="*.ts"`, plus the same grep against `docs/decisions/0006-*.md`, `docs/decisions/0007-*.md`, and `docs/glossary.md`: the only two matches are inside `Interpretation.tsx` itself, and both are the disclaimer sentences stating what the section *never* does (`"-- 'worth investigating,' never 'you should migrate/add/buy.'"` and `"Never a recommendation to buy, migrate, or change infrastructure."`). **Zero real violations.**

### Rule-15 spot-check — did Interpretation & Key Takeaways avoid the finance project's mistake?
**Yes, confirmed directly, not inferred from the decision doc's own claim.** Live-rendered `/interpretation` shows exactly the decomposition decision 0006 planned in writing before the component was built: a one-sentence Lead ("The real signal here isn't dollar magnitude...") → a `StatHighlight` (20.59, headline anomaly z-score) → four real `Bullets` (each grounded in a specific real finding: the z=20.90 join query, the 86% redundant-query rate, AWS's honest flat-cost non-anomaly, Databricks' cost-visibility gap) → two "WORKED CASE" `Example` blocks (the redundant-query finding; the two independently-computed forecasts) → an explicit always-visible `Callout` restating the hard limit → a closing `StatHighlight` (202 real events). This is genuinely a mix of real components carrying differentiated content, not a wall of paragraph prose behind a `Card` wrapper — the exact failure mode Factor Lens shipped in Phase 10n/10o. Spot-checked Learning, Real World, and References alongside it with the same result (bullets/callouts/worked-examples throughout, confirmed on both desktop and 375px mobile).

### Rule 9b — builder credit
Confirmed live: "Ethan Verduzco" appears in the persistent footer (styled as a trailing code comment, `// built by Ethan Verduzco`) on every page tested, plus a full "Builder" block with a working GitHub-profile link on the About page.

### Theming
Dark mode (default) and light mode (theme toggle) both confirmed via screenshot on Overview and Results — clean palette swap, no broken contrast, charts re-themed correctly.

### Mobile (375px)
Confirmed across Overview, Inputs, Results (all four tabs, including `TracePath` cards), Learning (including the nested Optimization Rules `Tabs`), Glossary, Real World, References, Tools & Technologies, and About. Zero console errors or warnings captured on any page in this pass (Playwright console capture, all pages).

### Edge cases (roadmap's own named list)
- **Source with zero/near-zero activity** — Databricks (1 real record). Overview, Results, Forecast, and Optimizations all handle this honestly: no forecast row, no anomaly baseline, and explicit "structural gap, disclosed rather than papered over with a synthetic number" callouts, confirmed live, not fabricated placeholders.
- **Forecast built on too little history** — Snowflake's native-unit forecast is built on exactly 1 observed day; rendered with an honest "from 0.22 credits observed over 1 day(s)" caption rather than hiding the thinness or fabricating confidence.
- **Anomaly detection against a single/thin data point** — the backend correctly returns an explicit `insufficient_baseline` status (never a fabricated z-score) for 5 real Snowflake rows and for the AWS forecast-period row (0 other same-day observations), confirmed via direct API inspection. `AnomalyCard` has real, correct rendering support for this status (distinct muted badge, suppresses the null baseline line) — confirmed by reading the component. One minor observation, not a bug: the default Results → Anomalies view's `.slice(0, 12)` over an unsorted row list doesn't happen to surface one of these 5 rows in the current data ordering, so a visitor scanning only the default view won't visually see an `insufficient baseline` card without scrolling further in a future data state — the mechanism itself is proven correct (API + component + Learning's own worked explanation), just not guaranteed visible by default today.
- **A source collector temporarily unreachable** — architecturally this can't manifest as a live-request failure, since `app/` never calls a collector at request time (independently confirmed above); an outage only delays when a new raw partition lands, which the near-zero-activity Databricks case already demonstrates handling gracefully. Each collector's own HTTP-calling code (`collect.py`) explicitly catches `requests.HTTPError` rather than crashing uncontrolled — confirmed by reading the code directly.

## Findings

### Finding 1 — Results → Forecast tab silently ignores the Inputs source filter
**Severity: Minor (non-blocking).**
**Repro:** Set Inputs → Source to "Databricks" (or navigate directly to `/results?source=databricks`), then open the Forecast tab.
**Expected:** Either the Forecast tab respects the source scope (e.g. shows only Databricks' forecast state), or it's visually clear the tab always shows a fixed three-source breakdown regardless of the page-level filter banner above it.
**Actual:** The page header still shows `filtered: source=databricks`, but the Forecast tab renders the full, unfiltered AWS run-rate chart and Snowflake native-unit forecast exactly as if no filter were applied — confirmed both via direct Playwright interaction and by reading `Results.tsx` (`const forecast = useFetch(() => api.forecast(), [])`, no `sourceParam` passed, unlike every other tab's fetch call). Not a crash or bad data, just a misleading inconsistency between the filter banner and the tab's actual content.
**Scope:** `frontend/src/pages/Results.tsx`, Forecast tab only (Spend, Anomalies, and Optimizations tabs all correctly respect the source filter, confirmed).

### Finding 2 — Results → Spend tab's per-source stat cards ignore the date-range filter
**Severity: Minor/Moderate (non-blocking).**
**Repro:** `GET /api/spend?source=aws&start=2020-01-01&end=2020-01-02` (a real window with zero matching AWS records), or the equivalent in the UI via Inputs' date-range fields.
**Expected:** The "AWS — records" stat card at the top of the Spend tab reflects the filtered (zero) count, consistent with the activity chart and attribution table directly below it.
**Actual:** `by_source_date` and `by_attribution` correctly return empty (`[]`) and the UI correctly shows an empty chart plus "No attribution rows for this filter," but `totals_by_source` returns the same real, unfiltered count (33 AWS records) regardless of the date-range filter — confirmed identical whether or not `start`/`end` are passed. Confirmed live in the browser: the top-of-tab "AWS 33 records" card is visibly inconsistent with the empty chart/table one scroll below it on the exact same filtered view.
**Scope:** Backend aggregation (`app/data/loader.py` or `app/api/routes.py`'s `totals_by_source` computation) — the date-range filter is applied to two of the three `spend` response fields but not the third.

### Finding 3 — One literal HTML entity in JSX text (cosmetic, not a live bug)
**Severity: Minor (non-blocking, style only).**
`frontend/src/pages/ReferencesFormulas.tsx:115` writes `&gt;=` directly in JSX text instead of the literal character `>=`. Confirmed this renders correctly today (JSX text-node entity decoding), so it is **not** a live instance of the rule-16 bug class described in `docs/project-standards.md`. Recommend the one-line cleanup anyway (rule 16's own stated preference — literal character over entity-by-habit) so this text can't silently break if it's ever moved into a plain string/`data/*.ts` field later.

### Finding 4 — macOS `.pth`-hidden-file workaround needed to run the backend test suite locally, undocumented in a runnable form
**Severity: Minor (non-blocking, environment/DX only).**
`uv run pytest collectors analytics app` fails to even collect (`ModuleNotFoundError: No module named 'cross_cloud_spend_trace_analytics'`, etc.) on a fresh `uv sync` on this machine, reproducing the exact macOS `UF_HIDDEN` `.pth`-file bug decision 0002 already diagnosed. The fix (`chflags nohidden .venv/lib/python3.11/site-packages/*.pth`) is documented in prose inside decision 0002 but isn't captured anywhere a future session would actually run it (a README troubleshooting note, a Makefile/justfile target, or a `conftest.py` guard). Not a code defect — confirmed irrelevant to Linux/Docker — but worth a one-line README addition so this doesn't need re-diagnosing from scratch in a future session.

## Definition-of-done checklist (v1, from `docs/roadmap.md`)

1. **Spend broken down by source / query / job / model** — confirmed, real data, all three sources.
2. **Anomaly detection on cost spikes** — confirmed, leave-one-out z-score, real z=20.90/z=11.48 firing, `insufficient_baseline` handled explicitly rather than fabricated.
3. **Forecasted month-end bill, per source and combined** — confirmed, real run-rate/trend for AWS, real native-unit projections for Snowflake, Databricks' structural gap honestly disclosed rather than faked.
4. **Concrete, specific optimization suggestions grounded in ingested data** — confirmed, 4 rules firing on real data (8 suggestions, 2 quantified with real percentages), the roadmap's own literal Databricks example explicitly and honestly flagged as not buildable on this trial tier rather than silently dropped.
5. **`qa-tester` verification against real ingested data end-to-end** — this document.
6. **`cyber-security` pass on credential handling** — done in Phase 7 (decision 0008); this pass independently re-confirmed the zero-live-credential runtime claim.
7. **Full `docs/project-standards.md` compliance before sign-off** — verified above (rules 1, 2, 6, 8, 9a, 9b, 14, 15, 16); no violations found, four non-blocking findings logged.

## Recommendation

Ship. Route Findings 1–4 to `developer` as a quick, non-blocking follow-up batch (all four are small, well-scoped, independently fixable) — none of them should hold up Phase 9 (Publish, already in progress) or Phase 10 (Deploy). Separately, re-flag to Ethan that decision 0008's recommended credential rotation (AWS key, Databricks token, Snowflake password) still has not happened as of this pass, per the live-authenticating collector tests above — non-blocking for Phase 8, but should happen before Phase 10's deploy, consistent with decision 0008's own recommendation.
