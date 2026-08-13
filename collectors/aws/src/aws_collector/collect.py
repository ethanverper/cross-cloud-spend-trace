"""Maps Cost Explorer API responses onto `UsageRecord`s.

Exercises all three granted read actions:
`collect_cost_and_usage` (`ce:GetCostAndUsage`), `collect_cost_forecast`
(`ce:GetCostForecast`), `collect_service_dimension_values`
(`ce:GetDimensionValues`).
"""
from __future__ import annotations

import logging
from datetime import date, datetime, timedelta, timezone

from cross_cloud_spend_trace_common.schema import UsageRecord

logger = logging.getLogger(__name__)

SOURCE = "aws"


def _first_of_month(d: date) -> date:
    return d.replace(day=1)


def _add_month(d: date) -> date:
    if d.month == 12:
        return d.replace(year=d.year + 1, month=1)
    return d.replace(month=d.month + 1)


def _amount(metric: dict | None) -> float | None:
    if not metric or metric.get("Amount") is None:
        return None
    return float(metric["Amount"])


def collect_cost_and_usage(client, *, lookback_days: int = 14) -> list[UsageRecord]:
    """Daily cost + usage quantity grouped by AWS service, via
    `ce:GetCostAndUsage`. Cost Explorer's `End` is exclusive, so
    `end=today` covers activity through yesterday (today's own cost is
    still being finalized)."""
    end = date.today()
    start = end - timedelta(days=lookback_days)
    now = datetime.now(timezone.utc)

    response = client.get_cost_and_usage(
        TimePeriod={"Start": start.isoformat(), "End": end.isoformat()},
        Granularity="DAILY",
        Metrics=["UnblendedCost", "UsageQuantity"],
        GroupBy=[{"Type": "DIMENSION", "Key": "SERVICE"}],
    )

    records: list[UsageRecord] = []
    for result in response.get("ResultsByTime", []):
        period_start = date.fromisoformat(result["TimePeriod"]["Start"])
        for group in result.get("Groups", []):
            service = group["Keys"][0] if group.get("Keys") else "UNKNOWN"
            metrics = group.get("Metrics", {})
            cost = metrics.get("UnblendedCost")
            usage = metrics.get("UsageQuantity")
            records.append(
                UsageRecord(
                    source=SOURCE,
                    resource_type="cost_explorer_daily_service",
                    resource_id=f"{period_start.isoformat()}::{service}",
                    usage_date=period_start,
                    service=service,
                    cost_usd=_amount(cost),
                    cost_basis="billed",
                    usage_quantity=_amount(usage),
                    usage_unit=(usage or {}).get("Unit"),
                    raw_metadata={"time_period": result["TimePeriod"], "metrics": metrics},
                    ingested_at=now,
                )
            )
    logger.info("aws: fetched %d cost-and-usage records (%s to %s)", len(records), start, end)
    return records


def collect_cost_forecast(client) -> list[UsageRecord]:
    """Month-end cost forecast via `ce:GetCostForecast`. Forecast periods
    can't overlap already-final historical data, so `Start` is always
    tomorrow; `End` is the first of next month (or the month after, if
    tomorrow already falls on/after that boundary — e.g. run on the 31st)."""
    now = datetime.now(timezone.utc)
    today = date.today()
    tomorrow = today + timedelta(days=1)
    period_end = _first_of_month(_add_month(today))
    if tomorrow >= period_end:
        period_end = _first_of_month(_add_month(_add_month(today)))

    response = client.get_cost_forecast(
        TimePeriod={"Start": tomorrow.isoformat(), "End": period_end.isoformat()},
        Metric="UNBLENDED_COST",
        Granularity="MONTHLY",
    )

    total = response.get("Total", {})
    record = UsageRecord(
        source=SOURCE,
        resource_type="cost_forecast",
        resource_id=f"{tomorrow.isoformat()}::{period_end.isoformat()}",
        usage_date=tomorrow,
        period_start=datetime.combine(tomorrow, datetime.min.time(), tzinfo=timezone.utc),
        period_end=datetime.combine(period_end, datetime.min.time(), tzinfo=timezone.utc),
        cost_usd=_amount(total),
        cost_basis="forecast",
        usage_unit=total.get("Unit"),
        raw_metadata={"forecast_results_by_time": response.get("ForecastResultsByTime", [])},
        ingested_at=now,
    )
    logger.info("aws: fetched cost forecast for %s to %s", tomorrow, period_end)
    return [record]


def collect_service_dimension_values(client, *, lookback_days: int = 14) -> list[UsageRecord]:
    """Active SERVICE dimension values in the queried window, via
    `ce:GetDimensionValues` — a lightweight way to confirm which services
    actually generated cost/usage without a second `GetCostAndUsage` call."""
    end = date.today()
    start = end - timedelta(days=lookback_days)
    now = datetime.now(timezone.utc)

    response = client.get_dimension_values(
        TimePeriod={"Start": start.isoformat(), "End": end.isoformat()},
        Dimension="SERVICE",
        Context="COST_AND_USAGE",
    )

    records = []
    for entry in response.get("DimensionValues", []):
        value = entry.get("Value", "UNKNOWN")
        records.append(
            UsageRecord(
                source=SOURCE,
                resource_type="service_dimension_value",
                resource_id=f"{start.isoformat()}::{end.isoformat()}::{value}",
                usage_date=start,
                service=value,
                raw_metadata={"attributes": entry.get("Attributes", {})},
                ingested_at=now,
            )
        )
    logger.info("aws: fetched %d active service dimension values", len(records))
    return records
