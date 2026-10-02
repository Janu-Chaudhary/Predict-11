import type { PlayerFantasy } from "../../fantasy/types";
import { fmt, fmtPct } from "../format";
import type { BatterVsTypes, BowlerVsHands } from "../matchups";
import type { CompareEntry } from "../types";

export type Better = "high" | "low" | null;

export type Section = "Overview" | "Batting" | "Bowling" | "Fielding" | "Fantasy" | "Batting by phase" | "Bowling by phase" | "Matchups";

/**
 * One compared player: the compare/profile stat line plus the optional extras loaded per player
 * (seasons from the profile, Dream11 distribution, type/hand matchups). Missing extras read as "–".
 */
export type Subject = CompareEntry & {
  seasons?: number[];
  fantasy?: PlayerFantasy | null;
  vsTypes?: BatterVsTypes | null;
  vsHands?: BowlerVsHands | null;
};

export type MetricRow = {
  key: string;
  group: Section;
  label: string;
  /** Which direction wins; null = informational, never highlighted or tallied. */
  better: Better;
  value: (e: Subject) => number | null;
  display?: (e: Subject) => string;
  /** A value only competes for "best" when the sample behind it is big enough. */
  eligible?: (e: Subject) => boolean;
};

const finite = (v: number | null | undefined): v is number => typeof v === "number" && Number.isFinite(v);

/**
 * Indices of the best value in a row. Ties share the highlight. Nulls and ineligible entries
 * never win, and nothing is highlighted unless at least two entries compete.
 */
export function bestIndices(values: (number | null | undefined)[], better: Better, eligible?: boolean[]): number[] {
  if (!better) return [];
  const pool = values
    .map((v, i) => ({ v, i }))
    .filter((x): x is { v: number; i: number } => finite(x.v) && (eligible ? eligible[x.i] !== false : true));
  if (pool.length < 2) return [];
  const target = better === "high" ? Math.max(...pool.map((x) => x.v)) : Math.min(...pool.map((x) => x.v));
  const winners = pool.filter((x) => Math.abs(x.v - target) < 1e-9).map((x) => x.i);
  // Everyone tied → no information, no highlight.
  return winners.length === pool.length ? [] : winners;
}

/**
 * Bar length (0–100 % of the track) per value, so the best value fills the track:
 * higher-is-better → v / max; lower-is-better → min / v (a smaller economy draws a longer bar).
 * Informational rows scale like higher-is-better. Missing values → null (no bar).
 */
export function barWidths(values: (number | null | undefined)[], better: Better): (number | null)[] {
  const vals = values.filter(finite);
  if (vals.length === 0) return values.map(() => null);
  if (better === "low") {
    const min = Math.min(...vals);
    return values.map((v) => {
      if (!finite(v)) return null;
      if (v <= 0) return 100;
      return Math.max(0, Math.min(100, (Math.max(min, 0) / v) * 100));
    });
  }
  const max = Math.max(...vals);
  return values.map((v) => (!finite(v) ? null : max > 0 ? Math.max(0, Math.min(100, (v / max) * 100)) : 0));
}

const phase = (e: Subject, p: string) => e.batting_phases.find((x) => x.phase === p);
const bphase = (e: Subject, p: string) => e.bowling_phases.find((x) => x.phase === p);
const vsGroup = (e: Subject, g: string) => e.vsTypes?.by_group.find((x) => x.group === g || x.bowling_type === g);
const vsHand = (e: Subject, h: "R" | "L") => e.vsHands?.by_hand.find((x) => x.hand === h);
const MIN_BALLS = 30;
/** Fantasy rates compete from 5 scored matches. */
const MIN_FANTASY = 5;
const fantasyOk = (e: Subject) => (e.fantasy?.matches ?? 0) >= MIN_FANTASY;
const dismissals = (e: Subject) => e.fielding.catches + e.fielding.stumpings + e.fielding.run_outs;

export const COMPARE_ROWS: MetricRow[] = [
  { key: "matches", group: "Overview", label: "Matches", better: "high", value: (e) => e.matches },
  { key: "seasons", group: "Overview", label: "Seasons", better: "high", value: (e) => (e.seasons ? e.seasons.length : null) },
  { key: "ov_runs", group: "Overview", label: "Runs", better: "high", value: (e) => e.batting.runs },
  { key: "ov_wkts", group: "Overview", label: "Wickets", better: "high", value: (e) => e.bowling.wickets },
  { key: "ov_dis", group: "Overview", label: "Fielding dismissals", better: "high", value: dismissals },
  { key: "ov_fp", group: "Overview", label: "Fantasy pts / match", better: "high", value: (e) => e.fantasy?.mean ?? null, display: (e) => fmt(e.fantasy?.mean, 1), eligible: fantasyOk },

  { key: "runs", group: "Batting", label: "Runs", better: "high", value: (e) => e.batting.runs },
  { key: "inns", group: "Batting", label: "Innings", better: null, value: (e) => e.batting.innings },
  { key: "bat_avg", group: "Batting", label: "Average", better: "high", value: (e) => e.batting.average, display: (e) => fmt(e.batting.average, 1), eligible: (e) => e.batting.innings >= 5 },
  { key: "bat_sr", group: "Batting", label: "Strike rate", better: "high", value: (e) => e.batting.strike_rate, display: (e) => fmt(e.batting.strike_rate, 1), eligible: (e) => e.batting.balls >= MIN_BALLS },
  { key: "hs", group: "Batting", label: "Highest", better: null, value: (e) => (e.batting.highest ? parseInt(e.batting.highest, 10) : null), display: (e) => e.batting.highest ?? "–" },
  { key: "50s", group: "Batting", label: "50s", better: "high", value: (e) => e.batting.fifties },
  { key: "100s", group: "Batting", label: "100s", better: "high", value: (e) => e.batting.hundreds },
  { key: "4s", group: "Batting", label: "4s", better: "high", value: (e) => e.batting.fours },
  { key: "6s", group: "Batting", label: "6s", better: "high", value: (e) => e.batting.sixes },
  { key: "bat_dot", group: "Batting", label: "Dot ball %", better: "low", value: (e) => e.batting.dot_pct, display: (e) => fmtPct(e.batting.dot_pct), eligible: (e) => e.batting.balls >= MIN_BALLS },

  { key: "wkts", group: "Bowling", label: "Wickets", better: "high", value: (e) => e.bowling.wickets },
  { key: "overs", group: "Bowling", label: "Overs", better: null, value: (e) => e.bowling.balls, display: (e) => e.bowling.overs },
  { key: "econ", group: "Bowling", label: "Economy", better: "low", value: (e) => e.bowling.economy, display: (e) => fmt(e.bowling.economy, 2), eligible: (e) => e.bowling.balls >= MIN_BALLS },
  { key: "bowl_avg", group: "Bowling", label: "Average", better: "low", value: (e) => e.bowling.average, display: (e) => fmt(e.bowling.average, 1), eligible: (e) => e.bowling.wickets >= 3 },
  { key: "bowl_sr", group: "Bowling", label: "Strike rate", better: "low", value: (e) => e.bowling.strike_rate, display: (e) => fmt(e.bowling.strike_rate, 1), eligible: (e) => e.bowling.wickets >= 3 },
  { key: "best", group: "Bowling", label: "Best", better: null, value: () => null, display: (e) => e.bowling.best ?? "–" },
  { key: "3w", group: "Bowling", label: "3+ wicket hauls", better: "high", value: (e) => (e.bowling.balls > 0 ? e.bowling.three_plus : null) },
  { key: "bowl_dot", group: "Bowling", label: "Dot ball %", better: "high", value: (e) => e.bowling.dot_pct, display: (e) => fmtPct(e.bowling.dot_pct), eligible: (e) => e.bowling.balls >= MIN_BALLS },

  { key: "ct", group: "Fielding", label: "Catches", better: "high", value: (e) => e.fielding.catches },
  { key: "st", group: "Fielding", label: "Stumpings", better: "high", value: (e) => e.fielding.stumpings },
  { key: "ro", group: "Fielding", label: "Run-outs", better: "high", value: (e) => e.fielding.run_outs },
  {
    key: "dis_pm",
    group: "Fielding",
    label: "Dismissals / match",
    better: "high",
    value: (e) => (e.matches > 0 ? dismissals(e) / e.matches : null),
    display: (e) => fmt(e.matches > 0 ? dismissals(e) / e.matches : null, 2),
    eligible: (e) => e.matches >= 5,
  },

  { key: "f_m", group: "Fantasy", label: "Scored matches", better: null, value: (e) => e.fantasy?.matches ?? null },
  { key: "f_mean", group: "Fantasy", label: "Mean points", better: "high", value: (e) => e.fantasy?.mean ?? null, display: (e) => fmt(e.fantasy?.mean, 1), eligible: fantasyOk },
  { key: "f_med", group: "Fantasy", label: "Median", better: "high", value: (e) => e.fantasy?.median ?? null, display: (e) => fmt(e.fantasy?.median, 1), eligible: fantasyOk },
  { key: "f_p10", group: "Fantasy", label: "Floor (p10)", better: "high", value: (e) => e.fantasy?.p10 ?? null, display: (e) => fmt(e.fantasy?.p10, 1), eligible: fantasyOk },
  { key: "f_p90", group: "Fantasy", label: "Ceiling (p90)", better: "high", value: (e) => e.fantasy?.p90 ?? null, display: (e) => fmt(e.fantasy?.p90, 1), eligible: fantasyOk },
  { key: "f_cons", group: "Fantasy", label: "Consistency", better: "high", value: (e) => e.fantasy?.consistency ?? null, display: (e) => fmt(e.fantasy?.consistency, 0), eligible: fantasyOk },
  { key: "f_50", group: "Fantasy", label: "50+ point games", better: "high", value: (e) => e.fantasy?.pct_50 ?? null, display: (e) => fmtPct(e.fantasy?.pct_50, 0), eligible: fantasyOk },
  { key: "f_ppc", group: "Fantasy", label: "Points per credit", better: "high", value: (e) => e.fantasy?.ppc ?? null, display: (e) => fmt(e.fantasy?.ppc, 2), eligible: fantasyOk },

  ...(["powerplay", "middle", "death"] as const).map(
    (p): MetricRow => ({
      key: `sr_${p}`,
      group: "Batting by phase",
      label: `Strike rate · ${p === "powerplay" ? "powerplay" : p}`,
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
      label: `Economy · ${p === "powerplay" ? "powerplay" : p}`,
      better: "low",
      value: (e) => bphase(e, p)?.economy ?? null,
      display: (e) => fmt(bphase(e, p)?.economy, 2),
      eligible: (e) => (bphase(e, p)?.balls ?? 0) >= MIN_BALLS,
    }),
  ),
  ...(["pace", "spin"] as const).map(
    (g): MetricRow => ({
      key: `vs_${g}`,
      group: "Matchups",
      label: `Strike rate vs ${g}`,
      better: "high",
      value: (e) => vsGroup(e, g)?.strike_rate ?? null,
      display: (e) => fmt(vsGroup(e, g)?.strike_rate, 1),
      eligible: (e) => (vsGroup(e, g)?.balls ?? 0) >= MIN_BALLS,
    }),
  ),
  ...(["pace", "spin"] as const).map(
    (g): MetricRow => ({
      key: `vs_${g}_avg`,
      group: "Matchups",
      label: `Average vs ${g}`,
      better: "high",
      value: (e) => vsGroup(e, g)?.average ?? null,
      display: (e) => fmt(vsGroup(e, g)?.average, 1),
      eligible: (e) => (vsGroup(e, g)?.dismissals ?? 0) >= 3,
    }),
  ),
  ...(["R", "L"] as const).map(
    (h): MetricRow => ({
      key: `econ_${h}hb`,
      group: "Matchups",
      label: `Economy vs ${h === "R" ? "right" : "left"}-handers`,
      better: "low",
      value: (e) => vsHand(e, h)?.economy ?? null,
      display: (e) => fmt(vsHand(e, h)?.economy, 2),
      eligible: (e) => (vsHand(e, h)?.balls ?? 0) >= MIN_BALLS,
    }),
  ),
];

export const rowsFor = (groups: Section[], rows = COMPARE_ROWS) => rows.filter((r) => groups.includes(r.group));

/** Drop rows nobody has a value for (e.g. bowling economy when neither player bowled). */
export function visibleRows(players: Subject[], rows = COMPARE_ROWS): MetricRow[] {
  return rows.filter((r) => players.some((p) => finite(r.value(p)) || (r.display && r.display(p) !== "–")));
}

export function rowBest(row: MetricRow, players: Subject[]): number[] {
  return bestIndices(
    players.map(row.value),
    row.better,
    players.map((p) => (row.eligible ? row.eligible(p) : true)),
  );
}

/** A row is contested when it has a direction and at least two eligible values. */
export function contested(row: MetricRow, players: Subject[]): boolean {
  if (!row.better) return false;
  return players.filter((p) => finite(row.value(p)) && (row.eligible ? row.eligible(p) : true)).length >= 2;
}

export type Tally = { wins: number[]; contested: number };

/** Rows won per player (shared wins count for each) over the contested rows. */
export function tally(rows: MetricRow[], players: Subject[]): Tally {
  const wins = players.map(() => 0);
  let n = 0;
  for (const r of rows) {
    if (!contested(r, players)) continue;
    n += 1;
    for (const i of rowBest(r, players)) wins[i] += 1;
  }
  return { wins, contested: n };
}

/** "Kohli leads 7 of 10", "Level · 4 each of 9", or null when nothing is contested. */
export function tallyText(t: Tally, names: string[]): string | null {
  if (t.contested === 0 || names.length < 2) return null;
  const top = Math.max(...t.wins);
  const leaders = t.wins.flatMap((w, i) => (w === top ? [i] : []));
  if (top === 0) return `All level over ${t.contested}`;
  if (leaders.length > 1) return `Level · ${top} each of ${t.contested}`;
  return `${names[leaders[0]]} leads ${top} of ${t.contested}`;
}
