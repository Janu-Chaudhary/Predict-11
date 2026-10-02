import { getJson } from "../players/api";
import { comparison, explanation, matchDetail, matchRows, runs, telemetry } from "./normalize";
import type { Comparison, Explanation, MatchDetail, MatchRow, Phase, RunSummary, Telemetry } from "./types";

export const labKeys = {
  runs: () => ["lab", "runs"] as const,
  telemetry: (v: string) => ["lab", "telemetry", v] as const,
  matches: (v: string, phase: Phase) => ["lab", "matches", v, phase] as const,
  match: (v: string, id: number) => ["lab", "match", v, id] as const,
  explain: (v: string, matchId: number, playerId: string) => ["lab", "explain", v, matchId, playerId] as const,
  compare: (a: string, b: string) => ["lab", "compare", a, b] as const,
};

/** The run list changes when a training run lands; a run's artifacts never change. */
export const RUNS_STALE_MS = 30_000;
export const RUN_STALE_MS = 30 * 60_000;

const enc = encodeURIComponent;

export async function fetchRuns(signal?: AbortSignal): Promise<RunSummary[]> {
  return runs(await getJson("/model/runs", {}, signal));
}

export async function fetchTelemetry(version: string, signal?: AbortSignal): Promise<Telemetry> {
  return telemetry(await getJson(`/model/runs/${enc(version)}/telemetry`, {}, signal));
}

export async function fetchMatches(version: string, phase: Phase, signal?: AbortSignal): Promise<MatchRow[]> {
  return matchRows(await getJson(`/model/runs/${enc(version)}/matches`, { phase }, signal));
}

export async function fetchMatch(version: string, id: number, signal?: AbortSignal): Promise<MatchDetail> {
  return matchDetail(await getJson(`/model/runs/${enc(version)}/matches/${id}`, {}, signal));
}

export async function fetchExplain(version: string, matchId: number, playerId: string, signal?: AbortSignal): Promise<Explanation> {
  return explanation(await getJson(`/model/runs/${enc(version)}/explain`, { match_id: matchId, player_id: playerId }, signal));
}

export async function fetchCompare(a: string, b: string, signal?: AbortSignal): Promise<Comparison> {
  return comparison(await getJson("/model/compare", { a, b }, signal));
}
