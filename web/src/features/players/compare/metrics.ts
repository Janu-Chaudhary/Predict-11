import { fmt } from "../format";
import type { CompareEntry } from "../types";

export type Better = "high" | "low" | null;

export type MetricRow = {
  key: string;
  group: "Overview" | "Batting" | "Bowling" | "Fielding" | "Batting by phase" | "Bowling by phase";
  label: string;
  /** Which direction wins; null = informational, never highlighted. */
  better: Better;
  value: (e: CompareEntry) => number | null;
  display?: (e: CompareEntry) => string;
  /** A value only competes for "best" when the sample behind it is big enough. */
  eligible?: (e: CompareEntry) => boolean;
};

/**
 * Indices of the best value in a row. Ties share the highlight. Nulls and ineligible entries
 * never win, and nothing is highlighted unless at least two entries compete.
 */
export function bestIndices(values: (number | null | undefined)[], better: Better, eligible?: boolean[]): number[] {
  if (!better) return [];
  const pool = values
    .map((v, i) => ({ v, i }))
    .filter((x): x is { v: number; i: number } => typeof x.v === "number" && Number.isFinite(x.v) && (eligible ? eligible[x.i] !== false : true));
  if (pool.length < 2) return [];
  const target = better === "high" ? Math.max(...pool.map((x) => x.v)) : Math.min(...pool.map((x) => x.v));
  const winners = pool.filter((x) => Math.abs(x.v - target) < 1e-9).map((x) => x.i);
  // Everyone tied → no information, no highlight.
  return winners.length === pool.length ? [] : winners;
}

const phase = (e: CompareEntry, p: string) => e.batting_phases.find((x) => x.phase === p);
const bphase = (e: CompareEntry, p: string) => e.bowling_phases.find((x) => x.phase === p);
const MIN_BALLS = 30;

export const COMPARE_ROWS: MetricRow[] = [
  { key: "matches", group: "Overview", label: "Matches", better: "high", value: (e) => e.matches },

  { key: "runs", group: "Batting", label: "Runs", better: "high", value: (e) => e.batting.runs },
  { key: "inns", group: "Batting", label: "Innings", better: null, value: (e) => e.batting.innings },
  { key: "bat_avg", group: "Batting", label: "Average", better: "high", value: (e) => e.batting.average, display: (e) => fmt(e.batting.average, 1), eligible: (e) => e.batting.innings >= 5 },
  { key: "bat_sr", group: "Batting", label: "Strike rate", better: "high", value: (e) => e.batting.strike_rate, display: (e) => fmt(e.batting.strike_rate, 1), eligible: (e) => e.batting.balls >= MIN_BALLS },
  { key: "hs", group: "Batting", label: "Highest", better: null, value: (e) => (e.batting.highest ? parseInt(e.batting.highest, 10) : null), display: (e) => e.batting.highest ?? "–" },
  { key: "50s", group: "Batting", label: "50s", better: "high", value: (e) => e.batting.fifties },
  { key: "100s", group: "Batting", label: "100s", better: "high", value: (e) => e.batting.hundreds },
  { key: "4s", group: "Batting", label: "4s", better: "high", value: (e) => e.batting.fours },
  { key: "6s", group: "Batting", label: "6s", better: "high", value: (e) => e.batting.sixes },
  { key: "bat_dot", group: "Batting", label: "Dot ball %", better: "low", value: (e) => e.batting.dot_pct, display: (e) => fmt(e.batting.dot_pct, 1), eligible: (e) => e.batting.balls >= MIN_BALLS },

  { key: "wkts", group: "Bowling", label: "Wickets", better: "high", value: (e) => e.bowling.wickets },
  { key: "overs", group: "Bowling", label: "Overs", better: null, value: (e) => e.bowling.balls, display: (e) => e.bowling.overs },
  { key: "econ", group: "Bowling", label: "Economy", better: "low", value: (e) => e.bowling.economy, display: (e) => fmt(e.bowling.economy, 2), eligible: (e) => e.bowling.balls >= MIN_BALLS },
  { key: "bowl_avg", group: "Bowling", label: "Average", better: "low", value: (e) => e.bowling.average, display: (e) => fmt(e.bowling.average, 1), eligible: (e) => e.bowling.wickets >= 3 },
  { key: "bowl_sr", group: "Bowling", label: "Strike rate", better: "low", value: (e) => e.bowling.strike_rate, display: (e) => fmt(e.bowling.strike_rate, 1), eligible: (e) => e.bowling.wickets >= 3 },
  { key: "best", group: "Bowling", label: "Best", better: null, value: () => null, display: (e) => e.bowling.best ?? "–" },
  { key: "bowl_dot", group: "Bowling", label: "Dot ball %", better: "high", value: (e) => e.bowling.dot_pct, display: (e) => fmt(e.bowling.dot_pct, 1), eligible: (e) => e.bowling.balls >= MIN_BALLS },

  { key: "ct", group: "Fielding", label: "Catches", better: "high", value: (e) => e.fielding.catches },
  { key: "st", group: "Fielding", label: "Stumpings", better: "high", value: (e) => e.fielding.stumpings },
  { key: "ro", group: "Fielding", label: "Run-outs", better: "high", value: (e) => e.fielding.run_outs },

  ...(["powerplay", "middle", "death"] as const).map(
    (p): MetricRow => ({
      key: `sr_${p}`,
      group: "Batting by phase",
      label: `SR ${p === "powerplay" ? "powerplay" : p}`,
      better: "high",
      value: (e) => phase(e, p)?.strike_rate ?? null,
      display: (e) => fmt(phase(e, p)?.strike_rate, 1),
      eligible: (e) => (phase(e, p)?.balls ?? 0) >= MIN_BALLS,
    }),
  ),
  ...(["powerplay", "middle", "death"] as const).map(
    (p): MetricRow => ({
      key: `econ_${p}`,
      group: "Bowling by phase",
      label: `Econ ${p === "powerplay" ? "powerplay" : p}`,
      better: "low",
      value: (e) => bphase(e, p)?.economy ?? null,
      display: (e) => fmt(bphase(e, p)?.economy, 2),
      eligible: (e) => (bphase(e, p)?.balls ?? 0) >= MIN_BALLS,
    }),
  ),
];

/** Drop bowling rows when nobody bowled, batting rows when nobody batted. */
export function visibleRows(players: CompareEntry[], rows = COMPARE_ROWS): MetricRow[] {
  const anyBowl = players.some((p) => p.bowling.balls > 0);
  const anyBat = players.some((p) => p.batting.balls > 0);
  return rows.filter((r) => (r.group.startsWith("Bowling") ? anyBowl : r.group.startsWith("Batting") ? anyBat : true));
}

export function rowBest(row: MetricRow, players: CompareEntry[]): number[] {
  return bestIndices(
    players.map(row.value),
    row.better,
    players.map((p) => (row.eligible ? row.eligible(p) : true)),
  );
}
