import { API_URL } from "@/lib/env";

import type {
  FantasyLeaderboard,
  HeadToHead,
  MatchWorm,
  MatchSummary,
  PointsTable,
  Records,
  ScenarioRequest,
  Scenarios,
  SeasonStory,
  SeasonSummary,
  TeamSquad,
  TeamSummary,
  VenueList,
} from "./types";

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

type Query = Record<string, string | number | null | undefined>;

function url(path: string, query?: Query) {
  const qs = new URLSearchParams();
  for (const [k, v] of Object.entries(query ?? {})) if (v !== null && v !== undefined && v !== "") qs.set(k, String(v));
  const s = qs.toString();
  return `${API_URL}/api/v1${path}${s ? `?${s}` : ""}`;
}

async function request<T>(path: string, init: RequestInit & { query?: Query } = {}): Promise<T> {
  const { query, ...rest } = init;
  let res: Response;
  try {
    res = await fetch(url(path, query), { ...rest, headers: { accept: "application/json", ...rest.headers } });
  } catch (e) {
    if ((e as Error).name === "AbortError") throw e;
    throw new ApiError("Can't reach the stats API. Is the backend running?", 0);
  }
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = (await res.json()) as { detail?: unknown };
      if (typeof body.detail === "string") detail = body.detail;
    } catch {
      /* non-JSON error body */
    }
    throw new ApiError(detail || `Request failed (${res.status})`, res.status);
  }
  return (await res.json()) as T;
}

export const seasonApi = {
  seasons: (signal?: AbortSignal) => request<SeasonSummary[]>("/seasons", { signal }),
  teams: (signal?: AbortSignal) => request<TeamSummary[]>("/teams", { signal }),
  table: (year: number, afterMatch?: number | null, signal?: AbortSignal) =>
    request<PointsTable>(`/seasons/${year}/table`, { signal, query: { after_match: afterMatch } }),
  scenarios: (year: number, afterMatch?: number | null, signal?: AbortSignal) =>
    request<Scenarios>(`/seasons/${year}/scenarios`, { signal, query: { after_match: afterMatch } }),
  pickScenarios: (year: number, body: ScenarioRequest, signal?: AbortSignal) =>
    request<Scenarios>(`/seasons/${year}/scenarios`, {
      method: "POST",
      body: JSON.stringify(body),
      headers: { "content-type": "application/json" },
      signal,
    }),
  story: (year: number, signal?: AbortSignal) => request<SeasonStory>(`/seasons/${year}/story`, { signal }),
  headToHead: (a: string, b: string, opts: { season?: number | null; venue?: number | null } = {}, signal?: AbortSignal) =>
    request<HeadToHead>(`/teams/${encodeURIComponent(a)}/vs/${encodeURIComponent(b)}`, {
      signal,
      query: { season: opts.season, venue: opts.venue },
    }),
  records: (opts: { season?: number | null; venue?: number | null; limit?: number } = {}, signal?: AbortSignal) =>
    request<Records>("/records", {
      signal,
      query: { scope: opts.season ? "season" : "all", season: opts.season, venue: opts.venue, limit: opts.limit ?? 10 },
    }),
  matches: (opts: { season?: number | null; team?: string | null } = {}, signal?: AbortSignal) =>
    request<MatchSummary[]>("/matches", { signal, query: { season: opts.season, team: opts.team } }),
  venues: (signal?: AbortSignal) => request<VenueList>("/venues", { signal }),
  squad: (teamId: number, signal?: AbortSignal) => request<TeamSquad>(`/teams/${teamId}/squad`, { signal }),
  fantasyLeaders: (season: number, limit = 5, signal?: AbortSignal) =>
    request<FantasyLeaderboard>("/fantasy/leaderboard", { signal, query: { season, limit } }),
  worm: (matchId: number, signal?: AbortSignal) => request<MatchWorm>(`/home/worm/${matchId}`, { signal }),
};
