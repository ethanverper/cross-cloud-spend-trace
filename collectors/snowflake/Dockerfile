# Snowflake ACCOUNT_USAGE collector — one-shot batch job. See
# collectors/aws/Dockerfile for the workspace-build rationale (identical
# pattern, different package).
FROM ghcr.io/astral-sh/uv:python3.11-bookworm-slim
WORKDIR /workspace

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

COPY pyproject.toml uv.lock ./
COPY collectors/common/pyproject.toml collectors/common/pyproject.toml
COPY collectors/aws/pyproject.toml collectors/aws/pyproject.toml
COPY collectors/snowflake/pyproject.toml collectors/snowflake/pyproject.toml
COPY collectors/databricks/pyproject.toml collectors/databricks/pyproject.toml
RUN uv sync --frozen --no-dev --package spend-lens-snowflake-collector

COPY collectors/common/src collectors/common/src
COPY collectors/snowflake/src collectors/snowflake/src

ENTRYPOINT ["uv", "run", "--frozen", "--no-dev", "--package", "spend-lens-snowflake-collector", "python", "-m", "snowflake_collector"]
