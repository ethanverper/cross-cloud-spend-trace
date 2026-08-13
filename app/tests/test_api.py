"""Real, non-mocked tests against the Phase 5 JSON API. No live cloud calls
here (that's the collectors' own live-test suites, decision 0002 item 7) --
these assert against the real Parquet output Phase 2/3 already landed and
committed under data/raw and data/processed, so the exact numbers below
(29 AWS records, 167 Snowflake rows, 1 Databricks run, z=20.90) are real,
not fixtures.
"""
from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_overview_reports_real_source_counts():
    resp = client.get("/api/overview")
    assert resp.status_code == 200
    body = resp.json()
    counts = {s["source"]: s["record_count"] for s in body["sources"]}
    assert counts == {"aws": 29, "snowflake": 167, "databricks": 1}
    assert body["total_records"] >= 29 + 167 + 1


def test_overview_headline_anomaly_is_the_real_z20_9_outlier():
    resp = client.get("/api/overview")
    body = resp.json()
    anomaly = body["headline_anomaly"]
    assert anomaly is not None
    assert round(anomaly["z_score"], 2) == 20.90


def test_overview_has_four_core_concepts_matching_phase3():
    resp = client.get("/api/overview")
    ids = {c["id"] for c in resp.json()["concepts"]}
    assert ids == {"attribution", "anomaly", "forecast", "optimization"}


def test_filters_rejects_unknown_source_query_at_the_api_layer():
    resp = client.get("/api/spend", params={"source": "gcp"})
    assert resp.status_code == 400


def test_filters_date_range_matches_real_ingested_window():
    resp = client.get("/api/filters")
    body = resp.json()
    assert body["date_range"]["min"] is not None
    assert body["date_range"]["max"] is not None
    assert body["date_range"]["min"] <= body["date_range"]["max"]


def test_spend_filtered_by_aws_only_returns_aws_rows():
    resp = client.get("/api/spend", params={"source": "aws"})
    body = resp.json()
    assert all(r["source"] == "aws" for r in body["by_source_date"])
    assert len(body["by_source_date"]) > 0


def test_anomalies_endpoint_reports_two_real_anomalies():
    resp = client.get("/api/anomalies")
    body = resp.json()
    assert body["anomaly_count"] == 2


def test_optimizations_endpoint_reports_real_eight_suggestions():
    resp = client.get("/api/optimizations")
    body = resp.json()
    assert body["total_count"] == 8
    assert body["quantified_count"] == 2


def test_forecast_endpoint_reports_real_aws_run_rate_projection():
    resp = client.get("/api/forecast")
    body = resp.json()
    aws_row = next(r for r in body["by_source"] if r["source"] == "aws")
    assert round(aws_row["run_rate_month_end_projection"], 6) == round(0.0001439888, 6)


def test_meta_reports_builder_credit():
    resp = client.get("/api/meta")
    body = resp.json()
    assert body["builder_name"] == "Ethan Verduzco"
    assert "github.com" in body["builder_links"]["repo"]
