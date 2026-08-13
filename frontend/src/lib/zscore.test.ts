import { describe, expect, it } from "vitest"
import { computeLeaveOneOutZScore } from "./zscore"

// Real numbers, re-verified directly against data/processed/
// anomalies_snowflake_query_duration/run_date=2026-08-12/*.parquet for
// decision 0007 -- not transcribed from decision 0003's rounded prose.
describe("computeLeaveOneOutZScore", () => {
  it("matches the real headline anomaly (CUSTOMER JOIN ORDERS, z=20.90)", () => {
    const z = computeLeaveOneOutZScore(11899, 260.617021, 556.965851)
    expect(z).not.toBeNull()
    expect(z!).toBeCloseTo(20.896044, 4)
  })

  it("matches the real second anomaly (CREATE WORKSPACE, z=11.48)", () => {
    const z = computeLeaveOneOutZScore(1993, 167.929204, 159.047481)
    expect(z).not.toBeNull()
    expect(z!).toBeCloseTo(11.475006, 4)
  })

  it("returns exactly 0 when the value equals its own baseline mean", () => {
    expect(computeLeaveOneOutZScore(260.617021, 260.617021, 556.965851)).toBe(0)
  })

  it("returns null on a zero-variance baseline instead of dividing by zero", () => {
    expect(computeLeaveOneOutZScore(5, 5, 0)).toBeNull()
  })

  it("returns null on non-finite input", () => {
    expect(computeLeaveOneOutZScore(NaN, 1, 1)).toBeNull()
  })
})
