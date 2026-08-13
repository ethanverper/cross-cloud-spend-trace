import { describe, expect, it } from "vitest"
import { formatDate, formatNumber, formatUsd, formatZScore } from "./format"

// Real-shaped inputs from this project's own actual data (decision 0002/
// 0003) -- not arbitrary fixtures. The whole reason formatUsd exists is
// that a naive 2-decimal currency formatter would round every one of these
// real sub-cent figures to "$0.00" and erase the actual data.
describe("formatUsd", () => {
  it("preserves real sub-cent AWS daily cost precision", () => {
    expect(formatUsd(0.0000046448)).toBe("$0.0000046448")
  })

  it("preserves the real AWS month-end run-rate projection", () => {
    expect(formatUsd(0.0001439888)).toBe("$0.0001439888")
  })

  it("formats zero exactly", () => {
    expect(formatUsd(0)).toBe("$0.00")
  })

  it("formats null/undefined as an em dash placeholder", () => {
    expect(formatUsd(null)).toBe("—")
    expect(formatUsd(undefined)).toBe("—")
  })

  it("formats amounts >= $1 with standard 2-decimal currency style", () => {
    expect(formatUsd(1234.5)).toBe("$1,234.50")
  })
})

describe("formatZScore", () => {
  it("matches the real headline anomaly's z-score to 2 decimals", () => {
    expect(formatZScore(20.896044071432563)).toBe("z=20.90")
  })

  it("matches the real second anomaly's z-score", () => {
    expect(formatZScore(11.475006)).toBe("z=11.48")
  })
})

describe("formatNumber", () => {
  it("formats the real Snowflake credit run-rate projection", () => {
    expect(formatNumber(6.902632205, 3)).toBe("6.903")
  })
})

describe("formatDate", () => {
  it("formats a real ingested-date ISO string", () => {
    expect(formatDate("2026-08-12")).toContain("2026")
  })

  it("passes through an unparseable value rather than throwing", () => {
    expect(formatDate("not-a-date")).toBe("not-a-date")
  })
})
