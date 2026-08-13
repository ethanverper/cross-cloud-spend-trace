# 0004. Rename spend-lens to cross-cloud-spend-trace

Date: 2026-08-13
Status: accepted

## Context

Only Phases 1-3 were complete when this decision was made (three live,
Dockerized collectors and the PySpark analytics core) — no frontend/
dashboard exists yet (that's Phase 5). Ethan requested the rename directly:
**spend-lens** felt too generic and read as copy-pasted from
`factor-lens`'s own naming pattern (Cowork OS's finance-domain project),
rather than describing what makes this project distinct. The mechanism
this project actually demonstrates is tracing cloud/warehouse spend back
to its exact source — the specific query, job, or pipeline responsible —
across multiple platforms (AWS, Snowflake, Databricks) at once. "Lens"
implies passive viewing; the real value here is active tracing/attribution
across three heterogeneous cost APIs, which "spend-lens" didn't
communicate.

## Decision

Renamed the project **spend-lens → cross-cloud-spend-trace** end to end:

- GitHub repo renamed to `github.com/ethanverper/cross-cloud-spend-trace`
  (GitHub preserves the old `spend-lens` URL as a redirect).
- Local project folder renamed
  `projects/technology/spend-lens/` → `projects/technology/cross-cloud-spend-trace/`,
  `git remote origin` updated to match.
- `README.md` title and prose updated to the new name.
- Every `pyproject.toml`'s `[project].name` (and the matching
  `[tool.uv.sources]`/dependency references) renamed from
  `spend-lens-*` to `cross-cloud-spend-trace-*` across all five uv
  workspace members (`common`, `aws`, `snowflake`, `databricks`,
  `analytics`); `uv.lock` regenerated to match.
- The two internal Python packages — `spend_lens_common` and
  `spend_lens_analytics` — renamed to `cross_cloud_spend_trace_common`
  and `cross_cloud_spend_trace_analytics` (directories moved, every
  import statement across all three collectors, `analytics/`, and their
  test suites updated). **Chose to do this rename**, unlike the
  distribution-name-only question it might otherwise have been reduced
  to, because: (1) it's a purely internal, unpublished workspace package
  with zero external consumers, so there's no compatibility surface to
  break; (2) the whole change is mechanical (directory move + import
  rename) and fully verified by the existing test suite immediately
  after; (3) the project is only 3 phases in — this is the cheapest point
  in its life to fix internal naming, before more code accumulates on top
  of it; (4) this repo's source *is* the deliverable a recruiter or
  engineer would actually read, so leaving `spend_lens_common` scattered
  through every import statement while everything else says
  "cross-cloud-spend-trace" would have been a visible, confusing
  mismatch on the one artifact this rename exists to fix.
- Every `Dockerfile` under `collectors/*/` updated (`--package` /
  `ENTRYPOINT --package` flags now reference the renamed distribution
  packages).
- `docs/roadmap.md`'s `Path:` header field updated to the new project
  path.
- Cosmetic/internal string literals with no external footprint (Spark
  `appName()` strings, a DBFS path prefix default that was never actually
  reachable — Phase 3's sync attempt 403'd before any file landed there,
  so no real DBFS state exists under the old path — a test function name,
  docstring prose) updated for consistency.

**Deliberately left unchanged** — real, live cloud resource identifiers
that Ethan actually created by hand in each console during Phase 1 and
that the collectors' credentials must still match exactly to authenticate:
the AWS IAM user `spend-lens-collector`, and the Snowflake
`SPEND_LENS_SVC` service user / `SPEND_LENS_READER` role /
`SPEND_LENS_WH` warehouse (referenced in `.env.example`, the AWS/Snowflake
collector docstrings, and `collectors/aws/tests/test_aws_collect.py`).
Renaming these strings in code would not rename the actual cloud
resources, and doing so would either break the collectors' live
authentication or misdescribe reality — worse than a naming
inconsistency. Renaming the resources themselves in AWS/Snowflake is out
of scope for this decision (no functional benefit, real risk of breaking
a working credential) and wasn't requested.

**Also deliberately left unchanged** — `docs/decisions/0001-0003` and the
phase-by-phase historical narrative in `docs/roadmap.md` (including its
own `# spend-lens — Roadmap` title and every in-body mention of
`spend-lens`, `spend_lens_common`, `spend_lens_analytics`, etc.). Those
documents are an honest record of real events — Ethan's own Phase 1
account-creation walkthrough, the real Databricks token-scope blocker
found in Phase 3 — as they happened when the project was still called
spend-lens. Rewriting them to say "cross-cloud-spend-trace" throughout
would be revisionist history, not documentation. Only the roadmap's
`Path:` metadata field (a pointer to where the project currently lives,
not a historical claim) was updated.

## Consequences

- The public repo, local folder, and every forward-facing name (README,
  package names, Docker) are now consistent under
  **cross-cloud-spend-trace**.
- Anyone reading `docs/decisions/0001-0003` or `docs/roadmap.md`'s phase
  narrative will correctly see the project referred to as "spend-lens" —
  this is intentional, not a missed rename, and future readers/agents
  should not "fix" it.
- `.venv` was rebuilt from scratch after the folder move (uv's console
  scripts bake in an absolute path at creation time, which broke after
  the directory rename) — a one-time, expected side effect of the rename,
  not a code change.
- Team-level docs (`docs/portfolio.md`, `docs/cadence.md`,
  `docs/ideation/index.md`, the ideation shortlist doc) were already
  updated directly by the orchestrating session before this decision was
  logged — out of this project's own scope to touch.
