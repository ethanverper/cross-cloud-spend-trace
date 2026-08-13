# 0005. Phase 4 brand identity direction

Date: 2026-08-13
Status: accepted

## Context

Phases 1-3 are done: three live, Dockerized collectors and a real PySpark
analytics core (unified model, leave-one-out z-score anomaly detection,
run-rate/trend forecast, a 4-rule optimization engine), all verified
against Ethan's actual AWS/Snowflake/Databricks accounts, not synthetic
data. No frontend exists yet — Phase 5 (`business-intelligence`) builds the
dashboard next. This decision sets the identity direction Phase 5 builds
against, per `docs/project-standards.md` rule 4 ("for a project's first
significant UI build... `brand-creative` sets direction before `developer`
implements it").

The project's name, **cross-cloud-spend-trace**, is fixed — decision 0004
renamed it deliberately, specifically because "spend-lens" read as a
copy-paste of `factor-lens`'s naming pattern and didn't communicate the
project's real differentiator: **actively tracing** spend back to its exact
source (query, job, pipeline) across three heterogeneous cloud APIs at
once, not passively viewing it. This decision does not revisit that
naming logic — it builds the visual/verbal system around it.

**Domain-matching call, made explicitly per the task brief**: this is a
cloud-cost/data-infrastructure observability tool, not a finance product.
The team's finance project (`factor-lens`) earned an institutional-register
identity (JPMorgan/Chase/Goldman-adjacent) because it's actually in that
register. Cross-cloud-spend-trace is not — defaulting to that register here
would import a look that fights what the product actually is (per this
agent's own standing mandate: "the identity must still serve the underlying
content"). Research below is grounded in genuinely comparable, currently
live cloud-cost/observability products instead.

## Research — real, live products actually browsed

Four products browsed live via the Browser tools (not reasoned from
training-data memory), chosen because they are genuinely comparable to this
project's actual domain (multi-cloud cost attribution / observability), not
because they're fashionable:

1. **Vantage (`vantage.sh`)** — the single most literally comparable
   product that exists: an actual multi-cloud, multi-SaaS, multi-AI-vendor
   cost allocation and optimization system of record. Browsed the live
   marketing site and embedded live product screenshots. Notable, real,
   concrete patterns: a stark black-on-white hero with no gradient,
   soft-pastel-dot legend for provider/vendor breakdown (a colored dot next
   to each vendor name — OpenAI, Anthropic, Cursor, Amazon Bedrock — rather
   than a color-only legend), a big black `$487,340` stat tile paired with a
   small pink percent-change pill (`-3.39%`), tabbed sub-views inside one
   card (`Overview` / `Anomalies`), and an actual `Recommendation` list with
   inline `Fix` action buttons on individual line items, not a separate
   "suggestions" page. **What's borrowed**: the colored-dot-plus-label
   pattern for source/vendor coding (cleaner than color-only, works in
   grayscale/accessibility contexts too), and the pattern of putting a
   fix/action directly on each optimization-suggestion row rather than
   making suggestions a passive read-only list.

2. **Datadog Cloud Cost Management (`datadoghq.com/product/cloud-cost-management`)**
   — browsed the live product page, which embeds a real product screenshot.
   Notable, real, concrete patterns: a near-black dashboard chrome with a
   left icon rail and a horizontal sub-tab bar (`Overview` / `Containers` /
   `GPU` / `Networking` / `Storage` / `SaaS Costs` / `AI Costs` / `Map`)
   nested under top-level tabs (`Summarize` / `Analyze` / `Optimize` /
   `Allocate` / `Plan`); a red-flagged **anomaly callout banner** sitting
   directly above the KPI row (`July daily average is projected to be
   $46.3K higher (+43%) than previous 2 months`) rather than buried in a
   separate alerts page; three flat KPI stat tiles side by side (month
   totals); a stacked, provider-colored bar chart as the primary chart form
   for multi-source spend over time, with the color legend directly below
   the chart, one swatch per real vendor (aws, Snowflake, Databricks,
   OpenAI, Anthropic, azure, gcp, etc. — this exact provider list
   corroborates that the three-source problem this project addresses is a
   real, live category others already chart this way). **What's
   borrowed**: leading with an anomaly/insight callout directly above the
   numbers rather than making a visitor infer it from a chart, and the
   stacked-bar-by-source chart form as the primary "where did the money go"
   visual.

3. **Honeycomb (`honeycomb.io`)** — browsed the live marketing homepage.
   Honeycomb is a distributed-tracing/observability product, not a cost
   tool, but it's the most direct analog for the actual *tracing* mechanism
   this project's name describes (following a signal back through a system
   to its origin, the same shape of problem as following a dollar back to
   the query that spent it). Notable, real pattern: a dark, monospace
   terminal-style panel embedded directly in the hero (not a screenshot of
   a chart, a literal terminal/log view) paired with a light gray marketing
   background and a single blue accent on the headline's first word only.
   **What's borrowed**: using monospace/terminal-style visual language as a
   legitimate hero device for a genuinely technical, engineer-facing
   product (not a gimmick) — reinforces this project's real register
   (Docker collectors, a Jobs API, `ACCOUNT_USAGE` views) rather than
   dressing it up as a consumer product.

4. **Vercel (`vercel.com` docs/pricing)** — browsed live. Named explicitly
   in the task brief as a comparable usage/billing-dashboard product.
   Vercel's own docs are set in **Geist Sans**, Vercel's real, open-source
   typeface (paired with **Geist Mono** for code/data), on a stark
   black-on-white ground with generous whitespace and no serif anywhere.
   **What's borrowed**: the Geist Sans/Mono pairing itself (see Typography
   below) — a real, live, production pairing, not an invented one.

**Explicitly not used as a reference**: Linear/Stripe/Mercury-style generic
modern-SaaS defaults (the team's own fallback per rule 4, absent
project-specific direction) and JPMorgan/Chase/Goldman-style institutional
finance (the register `factor-lens` correctly used, and which would be
wrong here — this product's users are data/platform engineers debugging a
bill, not fund managers or retail investors).

## Decision

### 1. Naming and wordmark treatment

The project name **cross-cloud-spend-trace** stays exactly as decision
0004 fixed it — no change proposed here. The identity treats the name's
own shape (lowercase, hyphenated, repo-like) as the design material, rather
than smoothing it into a conventional title-case logotype the way a
generic SaaS brand would.

**Primary lockup — a path/breadcrumb treatment**, styled to read
simultaneously as a Unix path and a GitHub `org/repo` string (which it
literally is: `ethanverper/cross-cloud-spend-trace`):

```
cross-cloud/  spend-trace
^ Geist Mono,          ^ Geist Sans, bold,
  text-muted-foreground   text-foreground, larger
  (the "namespace")       (the actual mark)
```

Rendered as a single inline lockup: `cross-cloud/` in Geist Mono at reduced
weight and a muted foreground color (the "namespace" prefix, like a scoped
npm package `@scope/name`), immediately followed by `spend-trace` in Geist
Sans Bold at full contrast (the actual reading mark). No icon/glyph mark —
a devtool-register product doesn't need an invented abstract logo the way
a consumer brand does, and Vantage/Honeycomb both lead with wordmark, not
icon, in their own primary lockups. A single thin signal-cyan (see Color,
below) underline draws left-to-right beneath `spend-trace` once on first
paint (not looping) — the one animated flourish in the whole lockup,
directly literalizing "trace" as a line being drawn under the product's own
name.

**Why this, not the obvious alternative**: the obvious alternative is a
conventional logotype — an icon plus "Spend Trace" in title case, the same
move Vantage makes with its own wordmark. That would borrow generic
consumer-SaaS polish this product doesn't need, and would obscure the real
differentiator (this is a literal path/attribution chain, source through
job through query) behind a smoothed-over brand mark. The path lockup keeps
the actual, real name intact and makes its own hyphenated structure work
for the identity instead of fighting it.

**Shortened spoken/display form**: "**Spend Trace**" (title case, space not
hyphen) for running prose, page titles, and anywhere the full technical
lockup would be clunky (e.g. a browser tab title, a spoken reference in
body copy: "Spend Trace flags this as a genuine anomaly, not a rule of
thumb"). The full `cross-cloud/spend-trace` lockup is reserved for the
actual masthead/header and footer credit line — the one or two places per
screen the full, precise name should appear. This mirrors how Honeycomb's
own nav shows the full `honeycomb.io` domain-style lockup while body copy
just says "Honeycomb."

### 2. Color story

**Base — near-black dark mode as the default, not an alternate theme.**
Data/platform engineers (this product's actual users) work in dark-mode-
heavy tools by default: Datadog's own Cloud Cost Management dashboard
(browsed above) ships dark by default, and Grafana/Databricks
notebooks/most terminal-adjacent tooling defaults dark too. `zinc-950`
(`#0A0A0B`, not pure `#000000` per the anti-slop skill's own guidance) as
the primary surface, `zinc-900`/`zinc-800` for elevated cards, `zinc-400`
for secondary text, `zinc-50` for primary text. A light theme is still
built (rule 6C/8B of the design skill — dual-mode by default, never
light-only or dark-only) but dark is the one this product opens in.

**A single product accent, deliberately not orange, blue, or red** — those
three hues are reserved for the per-source data-viz coding (below), and
reusing one of them as the brand accent would make chart legends and brand
chrome visually collide. **Signal cyan** (`#22D3EE` on dark, `#0891B2` on
light for contrast) is the one accent used for CTAs, active nav state,
links, and the wordmark's trace-underline. Rationale: cyan/teal reads as
"a signal being traced" (an oscilloscope trace, a fiber/network line) —
distinct from any of the three real cloud providers' own brand colors, so
it never gets confused with the data it's charting, and distinct from
Vantage's own indigo-violet accent so this doesn't read as a copy of the
one product it's closest to.

**A fixed, separate three-color source palette** for AWS / Snowflake /
Databricks wherever the dashboard needs to attribute spend to a specific
source (charts, chips, the `TracePath` breadcrumb below) — never used as
brand chrome, only as categorical data-viz color:

| Source | Color | Rationale |
|---|---|---|
| AWS | `#F59E0B` (amber) | Evokes AWS's own orange without literally reproducing the trademarked hex, keeps it visually distinct from the signal-cyan accent |
| Snowflake | `#38BDF8` (sky blue) | Evokes Snowflake's own ice-blue brand register, distinct enough from signal-cyan to never be mistaken for the accent |
| Databricks | `#FB7185` (rose/coral) | Evokes Databricks' own red-orange brand register without collision with AWS's amber |

This three-color legend is used consistently everywhere a chart, chip, or
breadcrumb needs to say "this cost came from X" — same discipline the
`dataviz` skill requires for categorical color, and matching the real
pattern Datadog's own live dashboard uses (one fixed swatch per vendor,
reused everywhere).

**Semantic colors**: anomaly/alert red (`#EF4444`) reserved *only* for
genuine statistical anomalies (the leave-one-out z-score flags), never for
generic "warning" UI chrome — so when something is red, it means the
analytics core actually flagged it, not just "this number is large."
Positive/savings green (`#34D399`) reserved for the optimization rules
engine's quantified savings figures only.

### 3. Typography system

**Geist Sans + Geist Mono** — Vercel's own real, open-source, live pairing
(confirmed by browsing `vercel.com`'s own docs, set in this exact pairing).
Chosen for three concrete reasons, not "it looks clean":

1. **One type family across the whole system.** Geist Sans (display/body)
   and Geist Mono (data/code) share the same underlying design language and
   metrics, so a dollar figure in Mono sitting next to a headline in Sans
   reads as one coherent voice, not two unrelated fonts competing — the
   exact failure mode `design-taste-frontend`'s font-pairing guidance warns
   against.
2. **Mono is functional here, not decorative.** This product's actual
   content is Mono-native: SQL query snippets (`SELECT O_ORDERSTATUS, ...`),
   job IDs (`job_id=101154624149862`), warehouse names (`SPEND_LENS_WH`),
   dollar figures to six decimal places (`$0.0000046448/day`), and the
   wordmark's own `cross-cloud/` path prefix. A product that will render
   this much literal code-shaped content needs a real monospace face doing
   real work, not an afterthought for the odd code block.
3. **Explicitly not Inter.** Per the anti-slop skill's own default
   discouragement of Inter — Geist Sans is the deliberate, referenced
   substitute here, not an unexamined default.

**Scale**: display headlines `text-4xl`/`text-5xl` Geist Sans Bold,
tracking slightly tight; body `text-base` Geist Sans Regular,
`leading-relaxed`; all numeric data (stat tiles, table cells, chart axis
labels, timestamps) in Geist Mono, tabular-nums, so columns of dollar
figures actually align.

### 4. Motion / microinteraction language

Per rule 11a, restraint means nothing decorative for its own sake, not the
absence of interactivity. Every motion below is motivated (hierarchy /
storytelling / feedback / state transition) and specified concretely, not
described in the abstract — reference `gsap-core` for implementation,
`ui-ux-pro-max`'s motion-preset library for concrete easing/timing
patterns, `design-motion-principles` for the underlying rationale.

- **The signature move — `TracePath` connector animation.** The literal
  visual signature of this identity: whenever a chart segment, anomaly
  card, or suggestion row is hovered/expanded, a thin signal-cyan line
  animates (stroke-dashoffset draw, ~250ms ease-out, GSAP or CSS) from the
  chart element to its attribution detail (source icon → job/query
  identifier → cost figure) — literally drawing the trace the product's
  name promises. This is the one place elaborate motion is justified: it's
  not decoration, it's the product demonstrating its own mechanism.
- **Stat-tile count-up on first mount.** KPI numbers (total spend,
  forecasted month-end bill) animate from 0 to their real value once on
  first render (~600-800ms, eased), matching the pattern both Vantage's and
  Datadog's own live dashboards use for their stat tiles — motivated by
  feedback (the number visibly "resolving" to its final state, not a
  static print).
- **Anomaly callout: one restrained pulse, not a loop.** When a genuine
  z-score anomaly is present (the real ones: the 20.90-z Snowflake query,
  the 11.48-z `CREATE WORKSPACE` call), its callout gets a single glow
  pulse on first mount, then settles static — draws the eye once, doesn't
  nag.
- **Forecast chart: line-draw reveal.** The month-end forecast line
  animates in with a stroke-dashoffset draw extending left-to-right on
  first view, representing the projection literally extending into the
  future — motivated by storytelling (watching the trend project forward
  is the forecast's actual message).
- **Tab/section transitions.** Cross-fade + 8px vertical slide (~180ms
  ease-out) between dashboard sub-views (Overview / Sources / Anomalies /
  Forecast / Suggestions), matching Datadog's own tabbed sub-nav pattern
  observed live.
- **Standard interactive states everywhere** (rule 11a's actual floor):
  button press (`scale-[0.98]`), card hover lift (`-translate-y-[1px]` +
  shadow), focus rings, skeleton loaders shaped like the real content
  they'll replace (not generic spinners) for any section waiting on a
  collector/pipeline read.
- **`prefers-reduced-motion` respected everywhere** — every animation above
  degrades to an instant state change, no exceptions.

### 5. Product personality

**Cross-Cloud Spend Trace reads like an instrument panel, not a sales
pitch: precise, low-drama, and always pointing at the exact source — it
never dresses up a number as more certain than the underlying data allows,
and it never asks an engineer to trust a claim it can't show the receipt
for.** Concretely: every anomaly, forecast, and suggestion this product
surfaces is traceable, in the UI, back to the specific real record that
produced it (the `TracePath` breadcrumb is the literal enforcement
mechanism for this) — the same honesty this project's own Phase 3 decision
doc (0003) already practices in writing (labeling structurally-correct-but-
not-yet-demonstrated results honestly rather than padding them).

### 6. Rule-14 landing/Overview screen spec

This project has no user-suppliable "sample portfolio" equivalent — the
real data *is* Ethan's own connected AWS/Snowflake/Databricks accounts
(205 real events across all three sources, verified in Phases 2-3, per
decisions 0002/0003). The landing screen does not ask a visitor to connect
anything or click "run demo" to populate synthetic data — **it opens
already loaded with this real, small-scale, honestly-labeled data**,
functioning as this project's actual equivalent of a one-click demo (rule
8): there's nothing to click to "make it real," it already is.

Concrete first-screen structure (all visible without scrolling or
interacting, per rule 14):

1. **Mechanism statement** (one sentence, literal, not a mission
   statement): *"cross-cloud-spend-trace traces AWS, Snowflake, and
   Databricks spend back to the exact query, job, or pipeline that caused
   it, and forecasts what the month will cost before the invoice arrives."*
2. **Connected-sources strip** (answers "what inputs does it need," named
   plainly, as three real-data chips, not a generic feature list): AWS
   (amber dot) · Snowflake (sky-blue dot) · Databricks (coral dot), each
   chip showing one real live figure pulled directly from the actual
   ingested store — e.g. "AWS · 29 daily cost records," "Snowflake · 167
   query-history rows," "Databricks · 1 job run" — making explicit that
   this reads from real connected accounts, not a mockup, and honestly
   showing Databricks' real thin data rather than padding it.
3. **Core-concepts row** (2-4 chips, per rule 14 — matches Phase 3's four
   real capabilities exactly, not invented marketing categories): **Cost
   Attribution** · **Anomaly Detection** · **Month-End Forecast** ·
   **Optimization Rules**.
4. **Real result preview** (not a stock illustration): a compact card
   showing one genuine, already-computed result directly on the landing
   screen — the real Snowflake anomaly (`z=20.90`, the unfiltered
   `CUSTOMER JOIN ORDERS` query) rendered as a small `TracePath` breadcrumb
   (Snowflake › `SPEND_LENS_WH` › that query id › `11,899ms`, `z=20.90`)
   sitting beside a small forecast sparkline for AWS's real $0.000144
   month-end projection. Both are real numbers already established in
   decision 0003, not placeholders.
5. **One-click entry point** (rule 8's demo action, surfaced here per rule
   14, adapted to this project's real shape): primary CTA reads **"Trace
   real spend →"**, not "Run demo" — clicking it routes straight into the
   populated Overview/Results dashboard (the same real 205-event dataset),
   with zero configuration step in between, because there's nothing to
   configure — the data is already real and already there.

### 7. Rule-15 content decomposition plan

Planned now, before `developer`/`business-intelligence` build anything,
per rule 15 and using `information-architecture`'s planning discipline.
Reusable primitives, defined once, reused everywhere (not invented per
section):

- **`Lead`** — one-sentence "so what," always the first line of any
  section with more than ~3 sentences of content.
- **`Bullets`** — for any enumerable set (never a comma-separated list
  inside a paragraph).
- **`Callout`** — always-visible aside for a caveat/definition/correction
  a reader would form a wrong mental model without (per rule 15's own
  callout-vs-footnote test).
- **`FootnoteMarker`/`Popover`** — click-gated, for genuinely optional
  depth (a citation, a cross-reference to a decision doc) that doesn't
  change the main claim's meaning.
- **`StatHighlight`** — a pulled-out number/claim, Geist Mono, signal-cyan
  or source-color depending on context.
- **`Example`** — a concrete worked case, visually set apart (bordered,
  slightly recessed card).
- **`TracePath`** — this project's own signature primitive (see Motion,
  above): a connected breadcrumb of source → job/query → cost, reused
  everywhere a specific attribution needs to be shown concretely, not
  described in prose.

Per-section plan:

**Real World / Corporate Applications** (owned by `brand-creative` per
rule 15's ownership line):
- `Lead`: "FinOps for data infrastructure is now a named discipline with
  dedicated tooling, not a spreadsheet exercise" (grounds it immediately in
  why this matters, not a mission statement).
- `Bullets`: 3-4 concrete corporate scenarios (a platform team catching a
  runaway Databricks job before month-end close, a data-eng manager
  explaining a bill spike to finance with an exact query cited instead of
  a shrug, an SRE team setting a budget alert against a forecasted
  month-end number instead of the actual invoice).
- `Callout`: a caveat that this class of tool augments but doesn't replace
  a dedicated FinOps practice/team at real scale — honest positioning, not
  oversell.
- `StatHighlight`: one real, sourced industry figure on cloud cost waste
  (to be sourced and cited at write time — not invented, per the anti-slop
  skill's "fake-precise numbers are flagged" rule) pulled out as the
  section's one number that matters.
- `Example`: one fully worked scenario, using this project's own real
  optimization-rule finding (the 86%-redundant repeated query, or the
  14-day-flat idle S3 charge) as the concrete case, not a generic story.

**Tools & Technologies** (owned by `brand-creative`, must read like a
hiring-manager checklist per rule 13, grouped by category with a
depth-of-use line per entry, not a tag cloud):
- *Languages*: Python (collectors, analytics core, all test suites).
- *Data/Analytics*: PySpark (unified model, leave-one-out z-score anomaly
  detection, `regr_slope`/`regr_intercept` trend forecast, 4-rule
  optimization engine — the actual statistical/aggregation core, not a
  keyword), Parquet (partitioned raw store, schema-enforced reads).
- *Cloud/Infra*: AWS Cost Explorer API + boto3 (real daily cost/forecast
  ingestion), Snowflake Connector + `ACCOUNT_USAGE` views (real
  query-history cost attribution), Databricks Jobs API (real job-run
  ingestion, plus the DBFS sync utility built and live-tested against a
  real, diagnosed token-scope 403), Docker (three independently
  containerized collectors), uv workspaces (five-member monorepo).
- *Frontend (Phase 5, forward-looking)*: React + Vite + TypeScript +
  Tailwind + shadcn/ui + a real charting library (`recharts`, per rule 4),
  GSAP for the `TracePath`/forecast-draw motion specified above.
- Each entry gets one line tying it to *this* project's actual real usage
  (per decisions 0002/0003's own real numbers), not a generic capability
  claim — `brand-creative` hands `business-intelligence` this exact
  structure, not a bare list, before Phase 5 implementation.

**References & Formulas** (owned by `brand-creative`):
- `Lead`: "Every number this product shows is computed by one of three
  documented methods, not a black box."
- Formula blocks (rendered properly, not prose-described) for: leave-one-
  out z-score, run-rate + trend (`regr_slope`/`regr_intercept`) forecast,
  and the 4 optimization rules' actual trigger conditions — each sourced
  directly to decision 0003's own real derivation and real verification
  numbers.
- `Callout` on the leave-one-out method specifically: why it's leave-one-
  out and not a naive in-group z-score (a naive score gets dragged toward
  its own outlier — the real reason this method was chosen, already
  documented in decision 0003, restated here for a visiting reader).
- `StatHighlight`/`Example`: the two real, live-verified anomalies
  (`z=20.90`, `z=11.48`) as the worked examples proving the formula fires
  on genuine data, not synthetic.

**Landing/Overview screen** (owned by `brand-creative`, structure specified
in Section 6 above): each of the five landing-screen elements is its own
primitive already (mechanism-statement `Lead`, connected-sources chips,
concept chips, a `TracePath` + sparkline result preview, one CTA) — no
paragraph block anywhere on this screen by construction.

### 8. Builder credit (rule 9b)

**Primary placement**: a persistent footer, present on every screen, set
in Geist Mono at reduced size — `Built by Ethan Verduzco` as a real link
(portfolio/LinkedIn/GitHub, whichever Ethan designates), styled like a
trailing code comment (`// built by Ethan Verduzco`), consistent with the
identity's technical/monospace register rather than a generic "made with
love by" footer line.

**Secondary placement**: an About/Credits panel reachable from the
persistent nav, giving the fuller real story (the actual build — three
live Dockerized collectors, real cloud accounts, the honest Phase 3
data-volume table) attributed to Ethan directly, not left for a visitor to
dig up in a README.

## Consequences

- Phase 5 (`business-intelligence`) implements against this spec directly:
  the `cross-cloud/spend-trace` path lockup, the near-black-default dark
  theme with signal-cyan accent and the fixed three-source data-viz
  palette, Geist Sans/Mono, the `TracePath` component as a real, reused
  primitive (not a one-off), the landing-screen structure in Section 6
  (opens already populated with real Phase 1-3 data, no connect-account
  step), and the Section 7 content-decomposition plan for Real World /
  Tools & Technologies / References / the landing screen.
- **What to preserve, nothing to discard**: there is no existing frontend
  implementation yet (Phase 5 hasn't started), so there's nothing being
  thrown out here — this is direction ahead of a first build, the cleanest
  point to set it, exactly as rule 4 intends.
- Rule 9a's Interpretation & Key Takeaways section (owned by
  `business-intelligence` per decision 0001's explicit ownership
  reassignment, since this project has no `quant-analyst` statistical-model
  mandate) is **not** planned here — its rule-15 decomposition duty follows
  its own content ownership, per rule 15's own corrected ownership line,
  and stays `business-intelligence`'s to plan before Phase 5 implementation
  touches it.
- The `TracePath` primitive is the one place this identity asks for real,
  non-trivial implementation work (SVG stroke-draw animation tied to
  hover/expand state) — flagged here explicitly so Phase 5 scopes it as a
  real component, not an afterthought bolted onto existing chart code.
- No architecture tradeoff is being forced by this direction — the team's
  already-mandated stack (React + Tailwind + shadcn/ui, rule 4) supports
  every element specified here (Geist via `next/font` or self-hosted
  `@font-face`, GSAP for the trace-draw motion, shadcn `Tabs`/`Card`/
  `Badge`/`HoverCard`/`Popover` for the structural primitives) with no
  need to escalate a different technical approach to `pm`/Ethan.
