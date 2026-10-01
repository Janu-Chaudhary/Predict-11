import { confidenceFor, type ConfidenceLevel, type ConfidenceThresholds } from "@/lib/confidence";

/**
 * Ball-count confidence for matchups (FEATURE-CATALOG D1; mirrors the API's PairStats.confidence):
 * low < 12 balls, medium 12–29, high ≥ 30.
 */
export const H2H_THRESHOLDS: ConfidenceThresholds = { medium: 12, high: 30 };

export function h2hConfidence(balls: number): ConfidenceLevel {
  return confidenceFor(balls, H2H_THRESHOLDS);
}

/** Prefer the server's label when it is one we know; fall back to the local rule. */
export function resolveConfidence(serverLevel: string | null | undefined, balls: number): ConfidenceLevel {
  return serverLevel === "low" || serverLevel === "medium" || serverLevel === "high" ? serverLevel : h2hConfidence(balls);
}
