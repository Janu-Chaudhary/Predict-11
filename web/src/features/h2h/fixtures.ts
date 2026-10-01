import type { PairStats } from "./types";

/** Live snapshot of V Kohli v JJ Bumrah (all IPL) for tests. */
export const KOHLI_V_BUMRAH: PairStats = {
  balls: 108, runs: 159, dismissals: 5, how_out: { caught: 3, lbw: 2 }, strike_rate: 147.22, average: 31.8,
  dot_pct: 36.11, boundary_pct: 20.37, fours: 16, sixes: 6, matches: 18, innings: 18, confidence: "high",
  by_season: [
    { season: 2024, balls: 3, runs: 0, dismissals: 1, strike_rate: 0 },
    { season: 2026, balls: 7, runs: 9, dismissals: 0, strike_rate: 128.57 },
  ],
  last_encounters: [
    { match_id: 1527693, date: "2026-04-12", season: 2026, venue: "Wankhede Stadium", balls: 7, runs: 9, out: false, how_out: null, summary: "7-9-0" },
    { match_id: 1426263, date: "2024-04-11", season: 2024, venue: "Wankhede Stadium", balls: 3, runs: 0, out: true, how_out: "caught", summary: "3-0-1" },
  ],
};
