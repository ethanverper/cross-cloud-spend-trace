import { useState } from "react"
import { computeLeaveOneOutZScore } from "@/lib/zscore"
import { StatHighlight } from "@/components/primitives/StatHighlight"
import { Callout } from "@/components/primitives/Callout"

// Real baseline for SPEND_LENS_WH's other same-day queries, re-verified
// against data/processed/anomalies_snowflake_query_duration/
// run_date=2026-08-12 (decision 0007) -- not rounded/approximated further
// than the source data already is.
const REAL_BASELINE_MEAN_MS = 260.617021
const REAL_BASELINE_STDDEV_MS = 556.965851
const REAL_BASELINE_N = 47
const REAL_ANOMALY_VALUE_MS = 11899
const REAL_ANOMALY_Z = 20.896044
const Z_THRESHOLD = 3

/**
 * Predict-then-reveal interactive check (project-standards rule 5): the
 * reader drags a hypothetical query duration and watches the real
 * leave-one-out z-score formula (frontend/src/lib/zscore.ts, the same
 * formula analytics/ computes in PySpark) score it live against the real
 * SPEND_LENS_WH baseline -- then can jump straight to the real value that
 * actually fired (11,899ms, z=20.90) to see how far past the threshold a
 * genuine anomaly lands.
 */
export function ZScoreExplorer() {
  const [value, setValue] = useState(Math.round(REAL_BASELINE_MEAN_MS))
  const z = computeLeaveOneOutZScore(value, REAL_BASELINE_MEAN_MS, REAL_BASELINE_STDDEV_MS)
  const fires = z !== null && Math.abs(z) >= Z_THRESHOLD
  const revealedReal = value === REAL_ANOMALY_VALUE_MS

  return (
    <div className="rounded-lg border border-border bg-muted/40 p-4 space-y-4">
      <div className="flex items-start justify-between gap-3 flex-wrap">
        <div>
          <div className="font-mono text-[11px] uppercase tracking-wide text-muted-foreground">
            Try it — real baseline, your hypothetical duration
          </div>
          <p className="text-xs text-muted-foreground mt-1 max-w-md">
            Baseline: {REAL_BASELINE_N} other real same-day queries on{" "}
            <span className="font-mono">SPEND_LENS_WH</span>, mean {REAL_BASELINE_MEAN_MS.toFixed(1)}ms, stddev{" "}
            {REAL_BASELINE_STDDEV_MS.toFixed(1)}ms.
          </p>
        </div>
        <StatHighlight
          value={z ?? 0}
          label="live z-score"
          color={fires ? "var(--anomaly)" : "var(--signal)"}
          size="sm"
          countUp={false}
          format={(n) => n.toFixed(2)}
        />
      </div>

      <input
        type="range"
        min={0}
        max={13000}
        step={50}
        value={value}
        onChange={(e) => setValue(Number(e.target.value))}
        className="w-full accent-signal"
        aria-label="Hypothetical query duration in milliseconds"
      />
      <div className="flex items-center justify-between text-xs font-mono">
        <span className="text-muted-foreground">{value.toLocaleString()}ms</span>
        <span className={fires ? "text-[var(--anomaly)]" : "text-muted-foreground"}>
          {fires ? `flagged — |z| ≥ ${Z_THRESHOLD}` : `not flagged — |z| < ${Z_THRESHOLD}`}
        </span>
      </div>

      <button
        type="button"
        onClick={() => setValue(REAL_ANOMALY_VALUE_MS)}
        className="text-xs font-mono text-signal underline underline-offset-2 hover:text-signal/80 active:scale-[0.98] transition-transform"
      >
        Reveal the real anomaly → {REAL_ANOMALY_VALUE_MS.toLocaleString()}ms (z={REAL_ANOMALY_Z.toFixed(2)})
      </button>

      {revealedReal && (
        <Callout tone="info">
          This is the real query that fired: an unfiltered{" "}
          <span className="font-mono">CUSTOMER JOIN ORDERS ... LIMIT 20</span> on{" "}
          <span className="font-mono">SPEND_LENS_WH</span>, 2026-08-12 — genuinely{" "}
          {REAL_ANOMALY_Z.toFixed(2)} standard deviations from that day's baseline, not a rounding artifact.
        </Callout>
      )}
    </div>
  )
}
