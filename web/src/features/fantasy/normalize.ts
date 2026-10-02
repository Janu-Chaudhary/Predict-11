/**
 * Adapters: raw JSON from /api/v1/fantasy/* (fantasy_schemas.py) → the view types in types.ts.
 * Readers tolerate missing keys so a contract wobble shows up as "–" in one cell rather than a
 * broken page.
 */
import { ROLES, type Role } from "@/lib/tokens";

import { teamCode } from "../players/format";
import type {
  CategoryMix,
  Distribution,
  FantasyPlayerRef,
  GameLog,
  Leaderboard,
  LeaderRow,
  MatchBestXi,
  MatchMeta,
  PlayerFantasy,
  SeasonBestXis,
  SeasonDistribution,
  SeasonMatchXi,
  SeasonXi,
  TeamOfSeason,
  Xi,
  XiPick,
} from "./types";

type Obj = Record<string, unknown>;

const isObj = (v: unknown): v is Obj => typeof v === "object" && v !== null && !Array.isArray(v);
const obj = (v: unknown): Obj => (isObj(v) ? v : {});
const arr = (v: unknown): unknown[] => (Array.isArray(v) ? v : []);

/** First finite number among the given keys. */
export function num(o: Obj, ...keys: string[]): number | null {
  for (const k of keys) {
    const v = o[k];
    if (typeof v === "number" && Number.isFinite(v)) return v;
  }
  return null;
}

export function str(o: Obj, ...keys: string[]): string | null {
  for (const k of keys) {
    const v = o[k];
    if (typeof v === "string" && v.trim() !== "") return v;
  }
  return null;
}

export function toRole(v: unknown): Role | null {
  if (typeof v !== "string") return null;
  const up = v.trim().toUpperCase();
  return (ROLES as readonly string[]).includes(up) ? (up as Role) : null;
}

/** TeamRef {id, name, short_code} or a plain name/code → badge code. */
export function teamOf(v: unknown): string | null {
  if (typeof v === "string") return teamCode(v);
  const o = obj(v);
  return str(o, "short_code") ?? teamCode(str(o, "name"));
}

const teamName = (v: unknown): string | null => (typeof v === "string" ? v : str(obj(v), "name"));

export function playerRef(raw: unknown): FantasyPlayerRef | null {
  const o = obj(raw);
  const id = str(o, "id");
  if (!id) return null;
  return { id, name: str(o, "name") ?? id, display_name: str(o, "display_name"), image_url: str(o, "image_url") };
}

const refOr = (raw: unknown): FantasyPlayerRef => playerRef(raw) ?? { id: "", name: "Unknown player" };

/** Consistency 0–100 from cv (sd / mean); computed from sd and mean when cv is missing. */
export function consistencyScore(cv: number | null, mean?: number | null, sd?: number | null): number | null {
  const c = cv ?? (mean && sd !== null && sd !== undefined && mean > 0 ? sd / mean : null);
  if (c === null) return null;
  return Math.max(0, Math.min(100, 100 * (1 - c)));
}

export function distribution(raw: unknown): Distribution {
  const o = obj(raw);
  const mean = num(o, "mean");
  const sd = num(o, "sd");
  return {
    matches: num(o, "n", "matches") ?? 0,
    total: num(o, "total") ?? 0,
    mean,
    median: num(o, "median"),
    sd,
    p10: num(o, "p10", "floor"),
    p90: num(o, "p90", "ceiling"),
    max: num(o, "max"),
    consistency: consistencyScore(num(o, "cv"), mean, sd),
    pct_50: num(o, "pct_50_plus"),
    pct_100: num(o, "pct_100_plus"),
  };
}

function recentPoints(o: Obj): number[] {
  return arr(o.last10 ?? o.recent)
    .map((x) => (typeof x === "number" ? x : num(obj(x), "points")))
    .filter((x): x is number => x !== null);
}

export function leaderRow(raw: unknown): LeaderRow {
  const o = obj(raw);
  return {
    ...distribution(o),
    rank: num(o, "rank"),
    player: refOr(o.player),
    team: teamOf(o.team),
    role: toRole(o.role),
    credits: num(o, "credits"),
    ppc: num(o, "points_per_credit"),
    recent: recentPoints(o),
  };
}

export function leaderboard(raw: unknown): Leaderboard {
  const o = obj(raw);
  const rows = arr(o.rows).map(leaderRow);
  const credits_season = num(o, "credits_season");
  return {
    season: num(o, "season"),
    min_matches: num(o, "min_matches") ?? 0,
    credits_season,
    credits_available: credits_season !== null || rows.some((r) => r.credits !== null),
    total_players: num(o, "total_players"),
    rows,
  };
}

function categoryMix(raw: unknown): CategoryMix | null {
  if (!isObj(raw)) return null;
  const m = { batting: num(raw, "batting") ?? 0, bowling: num(raw, "bowling") ?? 0, fielding: num(raw, "fielding") ?? 0, lineup: num(raw, "lineup") ?? 0, bonuses: num(raw, "bonuses") ?? 0 };
  return Object.values(m).some((v) => v !== 0) ? m : null;
}

function gameLog(raw: unknown): GameLog {
  const o = obj(raw);
  return { match_id: num(o, "match_id") ?? 0, date: str(o, "date"), season: num(o, "season"), opponent: teamOf(o.opponent), points: num(o, "points") ?? 0 };
}

export function playerFantasy(raw: unknown): PlayerFantasy {
  const o = obj(raw);
  const seasons = arr(o.seasons).map((s): SeasonDistribution => {
    const so = obj(s);
    return { ...distribution(so), season: num(so, "season") ?? 0, team: teamOf(so.team), credits: num(so, "credits"), credits_season: num(so, "credits_season"), ppc: num(so, "points_per_credit") };
  });
  const last = arr(o.last10).map(gameLog);
  // Sparklines want oldest → newest whatever order the API uses.
  const chron = [...last].sort((a, b) => (a.date ?? "").localeCompare(b.date ?? ""));
  const latest = [...seasons].sort((a, b) => b.season - a.season)[0];
  return {
    ...distribution(o.distribution),
    player: refOr(o.player),
    role: toRole(o.role),
    team: latest?.team ?? null,
    credits: num(o, "credits"),
    credits_season: num(o, "credits_season"),
    ppc: num(o, "points_per_credit"),
    mix: categoryMix(o.category_mix),
    last10: chron,
    by_season: seasons,
  };
}

function xiPick(raw: unknown, captainId: string | null, vcId: string | null, naive: boolean): XiPick {
  const o = obj(raw);
  const player = refOr(o.player);
  const mult = num(o, "multiplier") ?? 1;
  const captain = captainId ? player.id === captainId : mult >= 2;
  const vc = vcId ? player.id === vcId : mult === 1.5;
  const points = num(o, "points", "total") ?? 0;
  return {
    player,
    team: teamOf(o.team),
    role: toRole(o.role) ?? "BAT",
    points,
    effective: num(o, "scored") ?? points * mult,
    projected: naive ? num(o, "value") : null,
    credits: num(o, "credits"),
    captain,
    vice_captain: vc,
    matches: num(o, "matches"),
    mean: num(o, "mean"),
  };
}

export function xi(raw: unknown, naive = false): Xi | null {
  if (!isObj(raw)) return null;
  const c = str(raw, "captain");
  const vc = str(raw, "vice_captain");
  const picks = arr(raw.players).map((p) => xiPick(p, c, vc, naive));
  return {
    picks,
    total: num(raw, "total") ?? picks.reduce((s, p) => s + p.effective, 0),
    credits_used: num(raw, "credits_used"),
    credits_constrained: raw.credits_constrained === true,
  };
}

function matchMeta(m: Obj): MatchMeta {
  return {
    match_id: num(m, "match_id", "id") ?? 0,
    date: str(m, "date"),
    season: num(m, "season"),
    match_number: num(m, "match_number"),
    stage: str(m, "stage"),
    home: teamOf(m.team1),
    away: teamOf(m.team2),
    home_name: teamName(m.team1),
    away_name: teamName(m.team2),
    venue: str(obj(m.venue), "name") ?? str(m, "venue"),
    result: str(m, "result_text"),
  };
}

export function matchBestXi(raw: unknown): MatchBestXi {
  const o = obj(raw);
  return {
    ...matchMeta(obj(o.match)),
    no_result: o.no_result === true,
    best: xi(o.best),
    best_with_credits: xi(o.best_with_credits),
    naive: xi(o.naive_form, true),
    gap: num(o, "gap"),
    credits_season: num(o, "credits_season"),
    without_credits: arr(o.without_credits).length,
  };
}

/**
 * The backend picks the season XI's C/VC (its two biggest scorers by the XI's metric). Older
 * responses without `captain` fall back to the same rule here.
 */
function seasonXi(raw: unknown): SeasonXi | null {
  if (!isObj(raw)) return null;
  const metric = raw.metric === "mean" ? "mean" : "total";
  const base = arr(raw.players).map((p) => xiPick(p, null, null, false));
  const key = (p: XiPick) => (metric === "mean" ? (p.mean ?? 0) : p.points);
  const order = [...base].sort((a, b) => key(b) - key(a));
  const cId = str(raw, "captain") ?? order[0]?.player.id;
  const vcId = str(raw, "vice_captain") ?? order[1]?.player.id;
  const picks = base.map((p) => {
    const captain = p.player.id === cId;
    const vice = p.player.id === vcId;
    return { ...p, captain, vice_captain: vice, effective: p.points * (captain ? 2 : vice ? 1.5 : 1) };
  });
  return { metric, min_matches: num(raw, "min_matches") ?? 1, picks, sum_total: num(raw, "sum_total") ?? 0, sum_mean: num(raw, "sum_mean") ?? 0 };
}

export function teamOfSeason(raw: unknown): TeamOfSeason {
  const o = obj(raw);
  return { season: num(o, "season") ?? 0, by_total: seasonXi(o.by_total), by_mean: seasonXi(o.by_mean) };
}

export function seasonBestXis(raw: unknown): SeasonBestXis {
  const o = obj(raw);
  const matches = arr(o.matches).map((m): SeasonMatchXi => {
    const mo = obj(m);
    return {
      ...matchMeta(mo),
      best_total: num(mo, "best_total") ?? 0,
      naive_total: num(mo, "naive_total"),
      gap: num(mo, "gap"),
      best_with_credits_total: num(mo, "best_with_credits_total"),
      captain: playerRef(mo.captain),
      top_scorer: playerRef(mo.top_scorer),
      top_points: num(mo, "top_points"),
    };
  });
  return {
    season: num(o, "season") ?? 0,
    credits_season: num(o, "credits_season"),
    matches,
    no_result_matches: arr(o.no_result_matches).length,
    mean_best: num(o, "mean_best"),
    max_best: num(o, "max_best"),
    mean_naive: num(o, "mean_naive"),
    mean_gap: num(o, "mean_gap"),
  };
}
