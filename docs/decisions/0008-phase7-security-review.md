# 0008. Phase 7 security review: multi-cloud credential handling

Date: 2026-08-13
Status: accepted

## Context

Phase 7 (`cyber-security`), per `docs/roadmap.md`, is a dedicated review of
credential storage/scoping across AWS, Snowflake, and Databricks, even
though every connection is meant to be read-only scope: least-privilege
verified against actual granted permissions (not just documentation),
secrets never baked into Docker images or committed to git (including a
targeted check for any trace of the real AWS key Ethan accidentally pasted
into chat during Phase 1), Docker image hygiene, blast-radius containment
per source, and logging/error-handling hygiene. This document records what
was actually checked, what was found, and what was fixed directly versus
handed back to `developer`.

**Method**: read every collector's actual client/collect/main code
(`collectors/aws`, `collectors/snowflake`, `collectors/databricks`) against
the documented granted scope; read every `Dockerfile` and
`docker-compose.yml`; ran `git log --all -p` over this project's full
commit history and grepped it for AWS-key-shaped strings (`AKIA[0-9A-Z]{16}`
and `ASIA...`), Databricks-token-shaped strings (`dapi[0-9a-f]+`), any
`.env`/`.env.*` file ever having been tracked, and any non-empty credential
assignment ever committed; checked `.gitignore`'s own history (not just its
current content); inspected `app/` (FastAPI) and `frontend/` for any
credential-handling code at all.

## Findings

### Finding 1 — CRITICAL, live incident (not a repo vulnerability, an operational incident from this review session)

**What happened**: while validating this review's own `docker-compose.yml`
fix (finding 2, below), running `docker compose config` to check the merged
config caused Docker Compose to interpolate Ethan's real local `.env` file's
values into this session's own tool output — the real AWS access key ID and
secret access key for `spend-lens-collector`, the real Databricks personal
access token, and the real Snowflake password for `SPEND_LENS_SVC` were all
printed in plaintext in this agent session, once, as a side effect of that
one validation command.

**Risk**: this is functionally the same class of exposure as the Phase 1
incident already on record (Ethan pasting a real AWS key into chat) — a
live credential value left this project's local, gitignored boundary and
entered an AI agent session transcript, which is not this project's
credential-storage trust boundary. Nothing was committed, logged to a file,
or transmitted anywhere beyond this session's own output, but the value
should now be treated as no longer fully confidential.

**Fix**: no further command in this review printed `.env` contents again
(the rest of the docker-compose.yml/`.dockerignore` validation was done via
`python3 -c "import yaml..."` reading the file structurally, with no `.env`
interpolation). This ADR does not repeat any of the actual values.
**This requires Ethan's action, not an agent's**: rotate all three
credentials as soon as convenient —
1. AWS: deactivate/delete the current `spend-lens-collector` access key in
   IAM, generate a new one, update local `.env` (and later, Railway's
   secret store per Phase 10).
2. Databricks: revoke the current personal access token (User Settings →
   Developer → Access tokens), generate a new one, update `.env`.
3. Snowflake: `ALTER USER SPEND_LENS_SVC SET PASSWORD = '<new password>'`,
   update `.env`.

None of these are exploitable by anyone outside this session (they were
never sent anywhere beyond this agent's own tool output), but rotating is
the correct, low-cost response to any credential value leaving its intended
storage boundary, however briefly — consistent with this project's own
Phase 1 precedent of rotating immediately rather than assessing risk first.

### Finding 2 — MEDIUM, fixed directly: all three collectors shared one another's credentials via `env_file: .env`

**Location**: `docker-compose.yml` (before this review's fix).

**Risk**: every one of the three collector services (`aws-collector`,
`snowflake-collector`, `databricks-collector`) used `env_file: - .env`,
which injects the *entire* `.env` file — all three sources' credentials —
into each container's process environment, regardless of which credentials
that specific collector's code actually uses. This directly fails the
roadmap's own stated Phase 7 requirement ("a compromised AWS credential
shouldn't expose Snowflake/Databricks access and vice versa"): a real
compromise of the `aws-collector` container (e.g. a malicious or vulnerable
transitive dependency in `boto3`/its dependency tree achieving code
execution) would have had direct read access to the Snowflake password and
Databricks token sitting in its own process environment too, even though
that container's own code never touches them. CWE-200 (exposure of
sensitive information to an unauthorized actor) / CWE-668 (exposure of
resource to wrong sphere), scoped to the container-process boundary.

**Fix (applied directly)**: replaced each service's `env_file: - .env`
with an explicit `environment:` block listing only that service's own
credential variables (`AWS_ACCESS_KEY_ID`/`AWS_SECRET_ACCESS_KEY` for
`aws-collector`; `SNOWFLAKE_ACCOUNT`/`SNOWFLAKE_USER`/`SNOWFLAKE_PASSWORD`/
`SNOWFLAKE_ROLE`/`SNOWFLAKE_WAREHOUSE` for `snowflake-collector`;
`DATABRICKS_HOST`/`DATABRICKS_TOKEN` for `databricks-collector`), using
Compose's `${VAR}` interpolation against the same single root `.env` file
(Compose auto-loads `.env` for file interpolation — a different mechanism
than `env_file:`, which injects the whole file into the *container*). This
keeps Ethan's single `.env` file as the one place he edits credentials,
while each container's actual process environment now only ever contains
its own source's secret. Verified structurally (`python3 -c "import
yaml..."` parsing the file and listing each service's `environment` keys)
without triggering Compose's variable interpolation, to avoid repeating
finding 1's exposure.

### Finding 3 — LOW, fixed directly: no `.dockerignore`

**Location**: repo root (all three Dockerfiles build with repo root as
context, per `docker-compose.yml`).

**Risk**: none of the three Dockerfiles' `COPY` instructions ever reference
`.env`, `.git/`, or `data/` — each one explicitly whitelists only
`pyproject.toml`/`uv.lock` and the specific `collectors/*/src` it needs, so
**no secret has ever actually been baked into an image layer** (confirmed
by reading every `COPY`/`ARG`/`ENV` line in all three Dockerfiles — no
`ARG` carries a credential, and no `ENV` sets one). However, without a
`.dockerignore`, the *build context* sent to the Docker daemon on every
build still includes `.env`, full `.git/` history, and any locally-landed
`data/raw/`/`data/processed/` output — low-severity build-time hygiene gap,
and one accidental future `COPY .` away from becoming a real image-layer
leak.

**Fix (applied directly)**: added `.dockerignore` at the repo root,
excluding `.env`/`.env.*` (keeping `!.env.example`), `.git/`, `data/`,
Python/`uv` artifacts, and `frontend/node_modules`/`frontend/dist`.

### Finding 4 — LOW, not fixed directly, recommended for `developer`: collectors run as root in their containers

**Location**: `collectors/aws/Dockerfile`, `collectors/snowflake/Dockerfile`,
`collectors/databricks/Dockerfile` — none define a `USER` instruction, so
each one-shot batch container runs as root (the `uv`-provided base image's
default).

**Risk**: low practical exploitability here specifically — these are
one-shot batch jobs (not long-running network-listening services), and the
credentials they hold are already least-privilege/read-only per finding
"least-privilege scoping" below — but running as root is still real,
avoidable blast-radius surface if a dependency compromise ever did achieve
code execution inside one of these containers (CWE-250, execution with
unnecessary privileges).

**Why not fixed directly**: this environment's Docker daemon is not running
here (`docker info` fails — the same disclosed gap decision 0002 item 8
already recorded for this project: no working container runtime in the
build/review sandbox). Adding a non-root `USER` is simple in principle, but
verifying it doesn't break the collectors' actual write access to the
bind-mounted `./data/raw` host directory (finding 2's own volume mount)
needs a real `docker compose build && docker compose run` against a live
daemon — exactly the hands-on step decision 0002 already deferred to
Ethan's own machine. Recommending `developer` add `RUN useradd -m
collector` + `USER collector` to each Dockerfile and verify locally, rather
than shipping an unverified change to how these containers write real
landed data.

## Verified clean — no finding

- **AWS least-privilege, verified against actual code, not just docs**:
  `collectors/aws/src/aws_collector/client.py` constructs exactly one
  boto3 client (`boto3.client("ce", ...)`), and grepping the entire AWS
  collector source tree for `boto3`/`.client(` turns up no S3, Lambda, or
  STS client anywhere. `collect.py` only calls `get_cost_and_usage`,
  `get_cost_forecast`, and `get_dimension_values` — the exact three actions
  documented as granted to `spend-lens-collector`. The code's own comments
  independently corroborate this ("This module never touches S3 or Lambda,
  and never calls `sts:GetCallerIdentity`") and match what's actually
  there.
- **Snowflake least-privilege, verified against actual code**:
  `collectors/snowflake/src/snowflake_collector/client.py` connects with
  role `SPEND_LENS_READER` (not `ACCOUNTADMIN`) and warehouse
  `SPEND_LENS_WH`; the only two SQL statements anywhere in the collector
  (`collect.py`) are `SELECT`s against `ACCOUNT_USAGE.QUERY_HISTORY` and
  `ACCOUNT_USAGE.WAREHOUSE_METERING_HISTORY` — no `INSERT`/`UPDATE`/
  `DELETE`/`DDL`/`GRANT` anywhere in collector code, consistent with
  `IMPORTED PRIVILEGES` + `USAGE` being sufficient.
- **Databricks scope — confirmed narrow, and this is a genuine
  least-privilege win worth stating plainly**: `collect.py` calls exactly
  `/api/2.1/jobs/runs/list`, `/api/2.1/jobs/runs/get`,
  `/api/2.0/clusters/get`, and `/api/2.0/clusters/events` — all within the
  `jobs`+`clusters` scope. The token's inability to reach `files`/
  `workspace`/`unity-catalog` (decision 0003) was originally surfaced as a
  Phase 3 blocker (it's why the analytics pipeline runs locally instead of
  on live Databricks compute), but from a security standpoint it is exactly
  correct: this credential *cannot* write to DBFS, browse the workspace, or
  touch Unity Catalog even if something in the collector or analytics code
  tried to (`analytics/.../databricks_sync.py`'s own live-tested 403s prove
  this, not just the token's stated intent) — a real, live-verified
  demonstration of least privilege holding under an actual attempted
  broader call, not just an assumption.
- **No trace of the Phase 1 accidentally-pasted AWS credential anywhere in
  this repo's git history.** `git log --all -p` over the entire project
  directory's history (18 commits, from the first Phase 2 commit onward —
  Phase 1 itself predates any commit here, consistent with it being a
  human-only, no-code phase) was grepped for `AKIA[0-9A-Z]{16}` and
  `ASIA[0-9A-Z]{16}` (AWS long-term/temporary key ID patterns): zero
  matches. `.env`/any `.env.*` file (other than the always-blank
  `.env.example`, which was committed once, in the very first commit, with
  every value left empty) was never tracked at any point in history. The
  only long base64/hex-looking strings anywhere in the full history diff
  are `npm` `package-lock.json` `sha512` integrity hashes (confirmed by
  inspecting their surrounding diff context) — not credentials.
- **`.gitignore` excluded `.env` from the very first commit that created
  it** (`3de6864`, Phase 2's own first commit) — there was never a window
  where `.env` was trackable-by-default before being ignored.
- **Blast-radius containment, credential loading path**: every collector
  reads only its own environment variables via a shared
  `require_env(name)` helper (`collectors/common/.../config.py`) — there is
  no shared "load all credentials" path; each collector's `client.py` calls
  `require_env` only for the variable names it itself needs. Combined with
  finding 2's fix, this now holds at both the code layer (already true
  before this review) and the container-process layer (fixed by this
  review).
- **Logging/error-handling hygiene**: grepped every collector and `app/`
  for credential-shaped variable names in logging/exception paths — no
  collector logs a credential value. All `logger.info`/`logger.warning`
  calls log counts, IDs, or `str(exc)` from `requests.HTTPError`/
  `snowflake.connector` exceptions, which (verified against the actual
  exception classes used) render as status code + URL, not headers or
  credentials. `app/` (the FastAPI backend) never touches any cloud
  credential at all — it only ever reads Phase 3's already-computed,
  pre-aggregated Parquet output via `app/data/loader.py`, confirmed by
  grepping `app/` and `frontend/src` for every credential env-var name used
  anywhere in the collectors: zero matches. This is a meaningful structural
  containment property worth naming explicitly: even a full compromise of
  the deployed dashboard/API process could not reach any live cloud
  credential, because it never holds one.
- **Docker image hygiene, beyond the findings above**: base image
  (`ghcr.io/astral-sh/uv:python3.11-bookworm-slim`) is the same pattern
  already used elsewhere in this codebase (`factor-lens/Dockerfile`), a
  single-stage build (no leftover build-only layer to strip, since `uv
  sync` installs from wheels with no compilation step here) — reasonable,
  not flagged as a separate finding beyond finding 4's root-user point.

## Consequences

- `docker-compose.yml` and `.dockerignore` are fixed in this same commit —
  no further code change needed for findings 2/3.
- Finding 4 (non-root container user) is handed to `developer`: add
  `USER` to all three Dockerfiles and verify with a real
  `docker compose build && docker compose run --rm <name>` against
  Ethan's own Docker runtime (the same hands-on Docker step already owed
  since decision 0002).
- Finding 1 (this session's own credential exposure via `docker compose
  config`) needs Ethan's direct action: rotate the AWS access key,
  Databricks token, and Snowflake password named above. This is
  independent of finding 2/3's code fixes and does not block Phase 7 from
  being marked done, the same way the original Phase 1 incident didn't
  block Phase 1 — but it should happen before Phase 10's deploy, and ideally
  before any further local `docker compose` work.
- No finding rises to the level of blocking Phase 8 (QA) or Phase 9
  (publish continuing) — nothing found was a credential ever exposed in
  code, git history, or a built image; the one real exposure (finding 1)
  was an agent-session-transcript event, not a repository vulnerability,
  and does not require code changes to close, only rotation.
- Recorded explicitly for whoever reads this later: this review's own
  validation step is itself a small, generalizable lesson —
  `docker compose config`/`docker compose up --dry-run`-style commands
  interpolate and print real `.env` values by design. Future reviews of
  this or other projects should validate Compose file structure via a
  non-interpolating method (e.g. parsing the YAML directly) rather than
  Compose's own config-resolution commands, when real secrets are present
  in the working `.env`.
