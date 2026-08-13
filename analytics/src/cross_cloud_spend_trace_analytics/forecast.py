"""Task 3 — month-end forecast: run-rate and trend-based projection from
partial-month data, per source and combined.

**Relationship to AWS's own Cost Explorer forecast (decision, see
docs/decisions/0003)**: this module computes its own forecast independently
and uniformly across all three sources, rather than deferring to AWS's
native forecast API — Snowflake and Databricks have no equivalent forecast
API to defer to (per decision 0002 items 5/6), so a per-source-specific
approach would mean two sources get no forecast at all. AWS's real,
already-landed `cost_forecast` record (`data/raw/aws/cost_forecast`) is not
discarded, though: `reconcile_with_aws_native_forecast()` joins it in
alongside our own computed number, as a real ground-truth comparison point,
not as the number actually used — surfaced, not silently overridden or
silently ignored.

**Only AWS currently has dollar-denominated actuals to forecast against.**
Snowflake's collector deliberately leaves `cost_usd` null for every record
(decision 0002 item 5 — no credit-to-dollar rate is exposed to a read-only
role) and Databricks' one real landed job run also has `cost_usd=None`
(serverless compute exposes no node type to price against — decision 0002
item 6). `month_end_forecast()` reports `status="no_cost_data"` for those
sources honestly rather than projecting a fabricated $0, and
`native_unit_forecast()` below provides a secondary, explicitly-non-dollar
run-rate (Snowflake credits, Databricks cluster-hours) so those sources
aren't forecast-blind entirely — just not in USD.
"""
from __future__ import annotations

import calendar
from datetime import date

from pyspark.sql import DataFrame
from pyspark.sql import functions as F
from pyspark.sql.window import Window

# cost_basis values that represent money actually spent (or a labeled,
# source-specific estimate of it) as opposed to a pre-existing forecast —
# see schema.py / decision 0002 item 2 for what each basis means.
ACTUAL_COST_BASES = ["billed", "estimated_list_price"]


def daily_cost_actuals(events_df: DataFrame) -> DataFrame:
    """Per (source, usage_date) total known-cost actuals — excludes rows
    whose `cost_basis` is itself a forecast (AWS's own `cost_forecast`
    table) so a forecast can't accidentally forecast off another forecast."""
    return (
        events_df.filter(F.col("cost_basis").isin(ACTUAL_COST_BASES))
        .filter(F.col("cost_usd").isNotNull())
        .groupBy("source", "usage_date")
        .agg(F.sum("cost_usd").alias("cost_usd_day"))
    )


def native_unit_forecast(events_df: DataFrame, as_of: date) -> DataFrame:
    """A secondary, explicitly-non-dollar run-rate per (source, usage_unit)
    for sources/records with no `cost_usd` at all — Snowflake's real
    credits burn (`WAREHOUSE_METERING_HISTORY`), Databricks' cluster-hours.
    Same run-rate math as `month_end_forecast()`, just in native units."""
    days_in_month = calendar.monthrange(as_of.year, as_of.month)[1]
    month_start = date(as_of.year, as_of.month, 1)

    daily = (
        events_df.filter(F.col("cost_usd").isNull())
        .filter(F.col("usage_quantity").isNotNull())
        .filter(F.col("usage_unit").isNotNull())
        .filter((F.col("usage_date") >= month_start) & (F.col("usage_date") <= F.lit(as_of)))
        .groupBy("source", "usage_unit", "usage_date")
        .agg(F.sum("usage_quantity").alias("usage_qty_day"))
    )

    return (
        daily.groupBy("source", "usage_unit")
        .agg(
            F.countDistinct("usage_date").alias("days_observed"),
            F.sum("usage_qty_day").alias("total_so_far"),
        )
        .withColumn("run_rate_per_day", F.col("total_so_far") / F.col("days_observed"))
        .withColumn("days_in_month", F.lit(days_in_month))
        .withColumn(
            "run_rate_month_end_projection",
            F.col("run_rate_per_day") * F.lit(days_in_month),
        )
    )


def month_end_forecast(
    events_df: DataFrame,
    as_of: date,
    *,
    group_cols: list[str] | None = None,
) -> DataFrame:
    """Per `group_cols` (default `["source"]`; pass `[]` for one combined
    row across all sources), projects month-end dollar cost two ways from
    the days observed so far in `as_of`'s calendar month:

    - **run-rate**: `(total cost so far / days observed) * days in month`.
    - **trend**: fits a line (via Spark SQL's `regr_slope`/`regr_intercept`)
      to *cumulative* cost vs. day-of-month, extrapolated to the last day
      of the month — reduces to the same answer as run-rate when daily
      cost is perfectly flat (see docs/decisions/0003 for why that's
      exactly what happens on today's real AWS data), and diverges once
      real day-to-day growth/decline shows up.

    `days_observed` counts distinct calendar days actually present in the
    data for the current month (not "today's day-of-month") — deliberately,
    so a source whose most recent 1-2 days haven't landed yet (e.g. AWS
    Cost Explorer's own data lag) doesn't have its rate diluted by days
    with no data. `confidence` is a plain days_observed bucket
    ("low"/"medium"/"high"), not a statistical confidence interval — this
    is a run-rate estimate, not a modeled interval.
    """
    if group_cols is None:
        group_cols = ["source"]

    days_in_month = calendar.monthrange(as_of.year, as_of.month)[1]
    month_start = date(as_of.year, as_of.month, 1)

    daily = daily_cost_actuals(events_df).filter(
        (F.col("usage_date") >= month_start) & (F.col("usage_date") <= F.lit(as_of))
    )

    if not group_cols:
        daily = daily.withColumn("_all", F.lit("all"))
        gcols = ["_all"]
    else:
        gcols = group_cols

    w = Window.partitionBy(*gcols).orderBy("usage_date")
    daily = daily.withColumn("day_of_month", F.dayofmonth("usage_date")).withColumn(
        "cumulative_cost_usd", F.sum("cost_usd_day").over(w)
    )

    agg = daily.groupBy(*gcols).agg(
        F.countDistinct("usage_date").alias("days_observed"),
        F.sum("cost_usd_day").alias("total_so_far"),
        F.regr_slope("cumulative_cost_usd", "day_of_month").alias("trend_slope_per_day"),
        F.regr_intercept("cumulative_cost_usd", "day_of_month").alias("trend_intercept"),
    )

    out = (
        agg.withColumn("days_in_month", F.lit(days_in_month))
        .withColumn("run_rate_per_day", F.col("total_so_far") / F.col("days_observed"))
        .withColumn(
            "run_rate_month_end_projection",
            F.col("run_rate_per_day") * F.lit(days_in_month),
        )
        .withColumn(
            "trend_month_end_projection",
            F.when(
                F.col("days_observed") >= 2,
                F.col("trend_intercept") + F.col("trend_slope_per_day") * F.lit(days_in_month),
            ),
        )
        .withColumn(
            "status",
            F.when(F.col("total_so_far").isNull(), F.lit("no_cost_data")).otherwise(
                F.lit("ok")
            ),
        )
        .withColumn(
            "confidence",
            F.when(F.col("days_observed") >= 7, F.lit("high"))
            .when(F.col("days_observed") >= 3, F.lit("medium"))
            .otherwise(F.lit("low")),
        )
    )
    if not group_cols:
        out = out.drop("_all")
    return out


def reconcile_with_aws_native_forecast(
    aws_month_end_row: DataFrame, native_cost_forecast_df: DataFrame
) -> DataFrame:
    """Joins our own AWS month-end projection against AWS Cost Explorer's
    real, already-landed native forecast record (`resource_type =
    "cost_forecast"`, `cost_basis = "forecast"`) as a side-by-side
    comparison — surfaced for sanity-checking, never used to overwrite our
    own number, since our method needs to work the same way across all
    three sources and Snowflake/Databricks have no native forecast to
    defer to either."""
    native = (
        native_cost_forecast_df.filter(F.col("resource_type") == "cost_forecast")
        .select(
            F.col("cost_usd").alias("aws_native_forecast_usd"),
            F.col("period_start").alias("aws_native_forecast_period_start"),
            F.col("period_end").alias("aws_native_forecast_period_end"),
        )
        .limit(1)
    )
    return aws_month_end_row.crossJoin(native)


__all__ = [
    "ACTUAL_COST_BASES",
    "daily_cost_actuals",
    "native_unit_forecast",
    "month_end_forecast",
    "reconcile_with_aws_native_forecast",
]
