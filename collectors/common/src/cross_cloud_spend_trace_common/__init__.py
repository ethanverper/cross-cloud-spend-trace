"""Shared building blocks used by every cross-cloud-spend-trace source collector.

Kept deliberately small: a normalized record schema (`schema.UsageRecord`),
a raw-store writer (`storage.write_records`), and environment-variable
helpers (`config`). Each source collector (AWS/Snowflake/Databricks) is its
own Dockerized service and depends on this package as a uv workspace member
— see `docs/decisions/0002-phase2-raw-store-and-collector-architecture.md`.
"""
