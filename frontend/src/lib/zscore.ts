// The same leave-one-out z-score formula analytics/src/spend_lens_analytics/
// anomaly.py computes in PySpark (decision 0003) -- extracted here as a
// small, independently-tested pure function so the Learning section's
// interactive ZScoreExplorer widget can't silently drift from the formula
// it's teaching.

/**
 * z = (value - baselineMean) / baselineStddev
 *
 * `baselineMean`/`baselineStddev` must already be computed leave-one-out
 * (excluding the row being scored from its own baseline) -- this function
 * only does the final division, it doesn't compute the baseline itself.
 * Returns `null` on a zero-variance baseline rather than dividing by zero,
 * matching the real pipeline's own handling (decision 0003).
 */
export function computeLeaveOneOutZScore(
  value: number,
  baselineMean: number,
  baselineStddev: number,
): number | null {
  if (!Number.isFinite(value) || !Number.isFinite(baselineMean) || !Number.isFinite(baselineStddev)) return null
  if (baselineStddev === 0) return null
  return (value - baselineMean) / baselineStddev
}
