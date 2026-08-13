"""Task 2 — anomaly detection on cost spikes.

Statistical, not a hardcoded dollar threshold: for a chosen grain (e.g.
"each Snowflake query, baselined against every other query run in the same
warehouse the same day" or "each service's daily cost, baselined against
that service's own history"), compute the group's own mean/stddev and flag
rows whose value is more than `z_threshold` standard deviations above that
baseline.

Honest, load-bearing design point: this is a *leave-one-out* z-score. A
naive z-score computed with the outlier included in its own mean/stddev
gets dragged toward the outlier (one huge value inflates the very stddev
being used to judge it "not that unusual") — leave-one-out compares each
value against the baseline of *everything else* in its group, which is
closer to "a meaningful number of standard deviations above its own recent
baseline" as specified, and is also what actually lets a single genuine
outlier register a high z-score instead of a muted one.

A group needs at least `min_group_size` rows *excluding* the row being
scored for a baseline to mean anything — with fewer, `status` is
`"insufficient_baseline"`, not a fabricated z-score of 0. This matters for
this project specifically: Databricks has exactly one real job run landed
so far (see docs/roadmap.md Phase 2 entry), so every Databricks row will
report `insufficient_baseline` until more runs exist — a structural,
honestly-labeled outcome, not a bug.
"""
from __future__ import annotations

from pyspark.sql import Column, DataFrame
from pyspark.sql import functions as F
from pyspark.sql.window import Window


def detect_anomalies(
    df: DataFrame,
    *,
    group_cols: list[str],
    value_col: str,
    z_threshold: float = 3.0,
    min_group_size: int = 5,
    row_id_col: str | None = None,
) -> DataFrame:
    """Adds `group_n_other`, `baseline_mean`, `baseline_stddev`, `z_score`,
    `status` ("anomaly" | "normal" | "insufficient_baseline"), and
    `anomaly` (bool) columns to `df`.

    `row_id_col`, if given, is carried through unchanged so the caller can
    identify which specific record was scored — group_cols alone often
    isn't a unique key for a row (many rows share a group).
    """
    w = Window.partitionBy(*group_cols)

    n = F.count(F.col(value_col)).over(w)
    total = F.sum(F.col(value_col)).over(w)
    total_sq = F.sum(F.col(value_col) * F.col(value_col)).over(w)

    # Leave-one-out mean/variance for group size n, excluding the current
    # row: mean_loo = (total - x) / (n - 1); var_loo derived the same way
    # from sum-of-squares minus this row's own square contribution.
    n_other = n - F.lit(1)
    sum_other = total - F.col(value_col)
    sum_sq_other = total_sq - (F.col(value_col) * F.col(value_col))

    mean_other = F.when(n_other > 0, sum_other / n_other)
    # Population variance of the "other" values: E[x^2] - E[x]^2, clamped
    # to >= 0 to guard floating-point rounding producing a tiny negative.
    var_other = F.when(
        n_other > 0,
        F.greatest(
            (sum_sq_other / n_other) - (mean_other * mean_other),
            F.lit(0.0),
        ),
    )
    stddev_other = F.when(n_other > 0, F.sqrt(var_other))

    has_baseline = n_other >= F.lit(min_group_size)

    # Guard divide-by-zero: a baseline with zero variance (every other
    # value identical, e.g. AWS's flat $0.000005/day S3 charge — see
    # decision 0003) means *any* deviation is meaningful, but a value
    # equal to that constant baseline is by definition not an anomaly.
    z = F.when(
        has_baseline,
        F.when(
            stddev_other > F.lit(1e-12),
            (F.col(value_col) - mean_other) / stddev_other,
        ).otherwise(
            F.when(F.col(value_col) > mean_other, F.lit(float("inf"))).otherwise(F.lit(0.0))
        ),
    )

    out = (
        df.withColumn("group_n_other", n_other)
        .withColumn("baseline_mean", mean_other)
        .withColumn("baseline_stddev", stddev_other)
        .withColumn("z_score", z)
        .withColumn(
            "status",
            F.when(~has_baseline, F.lit("insufficient_baseline"))
            .when(z > F.lit(z_threshold), F.lit("anomaly"))
            .otherwise(F.lit("normal")),
        )
        .withColumn("anomaly", F.col("status") == F.lit("anomaly"))
    )
    return out


__all__ = ["detect_anomalies"]
