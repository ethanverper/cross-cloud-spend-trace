# AWS Cost Explorer collector — one-shot batch job, not a long-running
# server: `docker compose run --rm aws-collector` executes one collection
# pass and exits. Built from the repo-root uv workspace (see
# docs/decisions/0002-...md) so it can depend on the shared
# `cross-cloud-spend-trace-common` package without vendoring/duplicating it.
FROM ghcr.io/astral-sh/uv:python3.11-bookworm-slim
WORKDIR /workspace

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Workspace + member manifests first (own layer, cached across source-only
# changes). uv needs every declared workspace member's pyproject.toml
# present to resolve the workspace, even though only one package is synced.
COPY pyproject.toml uv.lock ./
COPY collectors/common/pyproject.toml collectors/common/pyproject.toml
COPY collectors/aws/pyproject.toml collectors/aws/pyproject.toml
COPY collectors/snowflake/pyproject.toml collectors/snowflake/pyproject.toml
COPY collectors/databricks/pyproject.toml collectors/databricks/pyproject.toml
RUN uv sync --frozen --no-dev --package cross-cloud-spend-trace-aws-collector

# Actual source, last (changes here shouldn't invalidate the dependency layer).
COPY collectors/common/src collectors/common/src
COPY collectors/aws/src collectors/aws/src

ENTRYPOINT ["uv", "run", "--frozen", "--no-dev", "--package", "cross-cloud-spend-trace-aws-collector", "python", "-m", "aws_collector"]
