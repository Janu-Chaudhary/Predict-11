/**
 * SAMPLE DATA for layout previews only. Nothing here is real or a prediction; every page that
 * renders it shows a "Sample data" note. Delete each block as its endpoint lands.
 */

import type { MatchResult } from "@/components/data/form-strip";
import type { TeamCode } from "./tokens";

export type PointsRow = {
  pos: number;
  team: TeamCode;
  p: number;
  w: number;
  l: number;
  nr: number;
  nrr: number;
  pts: number;
  form: MatchResult[];
};

export const SAMPLE_POINTS_TABLE: PointsRow[] = [
  { pos: 1, team: "PBKS", p: 14, w: 9, l: 4, nr: 1, nrr: 0.41, pts: 19, form: ["W", "W", "L", "W", "W"] },
  { pos: 2, team: "RCB", p: 14, w: 9, l: 5, nr: 0, nrr: 0.3, pts: 18, form: ["W", "L", "W", "W", "W"] },
  { pos: 3, team: "GT", p: 14, w: 8, l: 5, nr: 1, nrr: 0.25, pts: 17, form: ["L", "W", "W", "W", "L"] },
  { pos: 4, team: "MI", p: 14, w: 8, l: 6, nr: 0, nrr: 1.14, pts: 16, form: ["W", "W", "L", "L", "W"] },
  { pos: 5, team: "DC", p: 14, w: 7, l: 6, nr: 1, nrr: 0.01, pts: 15, form: ["L", "L", "W", "NR", "W"] },
  { pos: 6, team: "SRH", p: 14, w: 6, l: 7, nr: 1, nrr: -0.24, pts: 13, form: ["W", "L", "W", "L", "L"] },
  { pos: 7, team: "LSG", p: 14, w: 6, l: 8, nr: 0, nrr: -0.38, pts: 12, form: ["L", "W", "L", "L", "W"] },
  { pos: 8, team: "KKR", p: 14, w: 5, l: 8, nr: 1, nrr: -0.31, pts: 11, form: ["L", "NR", "L", "W", "L"] },
  { pos: 9, team: "RR", p: 14, w: 4, l: 10, nr: 0, nrr: -0.55, pts: 8, form: ["L", "L", "W", "L", "L"] },
  { pos: 10, team: "CSK", p: 14, w: 4, l: 10, nr: 0, nrr: -0.65, pts: 8, form: ["W", "L", "L", "L", "W"] },
];

export const SAMPLE_PLAYER = {
  name: "Sample Batter",
  team: "CSK" as TeamCode,
  role: "BAT" as const,
  detail: "RHB · Opener · 9.0 cr",
  tiles: { avgPts: 48.2, ceilP90: 96, captainRate: 18, matches: 14 },
  form: [31, 62, 18, 88, 44, 57, 70, 22, 49, 91],
  seasons: [
    { season: "2022", pts: 38.4, runs: 368 },
    { season: "2023", pts: 44.1, runs: 512 },
    { season: "2024", pts: 41.7, runs: 455 },
    { season: "2025", pts: 52.3, runs: 610 },
    { season: "2026", pts: 48.2, runs: 571 },
  ],
  log: [
    { date: "2026-05-18", opp: "MI", runs: 64, balls: 41, pts: 88, pred: 46 },
    { date: "2026-05-14", opp: "RCB", runs: 12, balls: 15, pts: 22, pred: 44 },
    { date: "2026-05-10", opp: "GT", runs: 51, balls: 38, pts: 70, pred: 45 },
    { date: "2026-05-06", opp: "KKR", runs: 38, balls: 29, pts: 57, pred: 47 },
    { date: "2026-05-02", opp: "DC", runs: 27, balls: 24, pts: 44, pred: 49 },
  ],
  matchups: [
    { bowler: "Right-arm fast", balls: 812, runs: 1120, outs: 31 },
    { bowler: "Left-arm orthodox", balls: 214, runs: 251, outs: 9 },
    { bowler: "Leg-spin", balls: 64, runs: 71, outs: 3 },
  ],
};

/** Cumulative runs by over for a 20-over innings, with wicket overs flagged. */
function worm(perOver: number[], wicketOvers: number[]) {
  let total = 0;
  return [{ over: 0, runs: 0 }].concat(
    perOver.map((r, i) => {
      total += r;
      return { over: i + 1, runs: total, wicket: wicketOvers.includes(i + 1) } as { over: number; runs: number; wicket?: boolean };
    }),
  );
}

const HOME_OVERS = [6, 11, 8, 14, 9, 12, 7, 6, 9, 8, 10, 7, 12, 9, 11, 13, 8, 15, 12, 9];
const AWAY_OVERS = [8, 5, 12, 7, 10, 9, 6, 8, 11, 5, 9, 12, 7, 6, 10, 9, 14, 7, 11, 10];

export const SAMPLE_WORM = {
  home: { team: "CSK", points: worm(HOME_OVERS, [3, 9, 14, 18, 20]) },
  away: { team: "MI", points: worm(AWAY_OVERS, [2, 6, 10, 13, 16, 17, 19, 20]) },
};

export const SAMPLE_MANHATTAN = HOME_OVERS.map((runs, i) => ({
  over: i + 1,
  runs,
  wickets: [3, 9, 14, 18, 20].includes(i + 1) ? 1 : 0,
}));
