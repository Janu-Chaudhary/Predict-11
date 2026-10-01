import { API_URL } from "@/lib/env";

import type { CompareResponse, PlayerProfile, SearchResponse, StatFilter } from "./types";

/** Error with the HTTP status so views can tell "not found" from "API down". */
export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number | null,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

/** GET a JSON endpoint under /api/v1 with typed result and a readable error. */
export async function getJson<T>(path: string, params: Record<string, string | number | undefined | null>, signal?: AbortSignal): Promise<T> {
  const qs = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) if (v !== undefined && v !== null && v !== "") qs.set(k, String(v));
  const url = `${API_URL}/api/v1${path}${qs.size ? `?${qs}` : ""}`;
  let res: Response;
  try {
    res = await fetch(url, { signal, headers: { accept: "application/json" } });
  } catch (e) {
    if ((e as Error).name === "AbortError") throw e;
    throw new ApiError("The stats API is unreachable.", null);
  }
  if (!res.ok) {
    let detail = `HTTP ${res.status}`;
    try {
      const body = (await res.json()) as { detail?: unknown };
      if (typeof body.detail === "string") detail = body.detail;
    } catch {
      /* keep status text */
    }
    throw new ApiError(detail, res.status);
  }
  return (await res.json()) as T;
}

export const filterParams = (f: StatFilter = {}) => ({ season: f.season, since: f.since });

export function fetchPlayerSearch(q: string, limit = 10, signal?: AbortSignal) {
  return getJson<SearchResponse>("/players/search", { q, limit }, signal);
}

export function fetchPlayerProfile(id: string, filter: StatFilter = {}, signal?: AbortSignal) {
  return getJson<PlayerProfile>(`/players/${encodeURIComponent(id)}`, filterParams(filter), signal);
}

export function fetchCompare(ids: string[], filter: StatFilter = {}, signal?: AbortSignal) {
  return getJson<CompareResponse>("/players/compare", { ids: ids.join(","), ...filterParams(filter) }, signal);
}
