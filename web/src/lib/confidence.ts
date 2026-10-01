/**
 * Sample-size → confidence cue. Used wherever a stat rests on a small n
 * (matchups, venue splits, H2H). §4.6: "n=64 · medium confidence"; n < 30 falls back to type-level data.
 */

export type ConfidenceLevel = "low" | "medium" | "high";

export type ConfidenceThresholds = {
  /** n at or above this is at least "medium". */
  medium: number;
  /** n at or above this is "high". */
  high: number;
};

export const DEFAULT_CONFIDENCE_THRESHOLDS: ConfidenceThresholds = { medium: 30, high: 100 };

export function confidenceFor(n: number, thresholds: ConfidenceThresholds = DEFAULT_CONFIDENCE_THRESHOLDS): ConfidenceLevel {
  if (!Number.isFinite(n) || n < thresholds.medium) return "low";
  if (n < thresholds.high) return "medium";
  return "high";
}
