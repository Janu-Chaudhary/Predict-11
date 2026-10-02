import { API_URL } from "@/lib/env";

import { planHero, resolveHero, type HeroPreview } from "./lib/rotation";
import type { HomeData, HomeState, HomeTiles, Standings, Wagon, Worm, XI } from "./types";

type Got<T> = { ok: true; data: T } | { ok: false; status: number };

/** Server-side GET against the API (no CORS involved). 204/404 are normal "no data" answers. */
async function get<T>(path: string, timeoutMs = 8000): Promise<Got<T>> {
  try {
    const res = await fetch(`${API_URL}/api/v1${path}`, {
      cache: "no-store",
      signal: AbortSignal.timeout(timeoutMs),
      headers: { accept: "application/json" },
    });
    if (res.status !== 200) return { ok: false, status: res.status };
    return { ok: true, data: (await res.json()) as T };
  } catch {
    return { ok: false, status: 0 };
  }
}

const orNull = <T>(g: Got<T>): T | null => (g.ok ? g.data : null);

/**
 * Everything the Home page needs, fetched on the server in parallel: hero state + the hero's
 * data (with the C worm as fallback) + bento tiles. `preview` (`?hero=A|B|C`) forces a concept;
 * in development it also turns on the documented shot-data dev fallback for the 2026 Final.
 */
export async function loadHome(preview: HeroPreview = null): Promise<HomeData> {
  const devSpike = preview === "A" && process.env.NODE_ENV !== "production";
  const q = devSpike ? "?dev_spike_wagon=true" : "";
  const [stateRes, tilesRes] = await Promise.all([get<HomeState>(`/home/state${q}`), get<HomeTiles>("/home/tiles")]);
  const tiles = orNull(tilesRes);
  const standingsP = tiles?.table ? get<Standings>(`/seasons/${tiles.table.season}/table`).then(orNull) : Promise.resolve(null);
  if (!stateRes.ok) {
    return {
      state: null,
      tiles,
      standings: await standingsP,
      hero: { kind: "none", note: "" },
      error: stateRes.status === 0 ? "The Predict-11 API is not reachable." : `The API answered ${stateRes.status}.`,
    };
  }
  const state = stateRes.data;
  const plan = planHero(state, preview);
  const id = plan.heroMatchId;
  const [standings, wagon, xi, worm] = await Promise.all([
    standingsP,
    plan.requested === "A" && id !== null ? get<Wagon>(`/home/wagon/${id}${q}`).then(orNull) : null,
    plan.requested === "B" && id !== null ? get<XI>(`/home/xi/${id}`).then(orNull) : null,
    plan.wormMatchId !== null ? get<Worm>(`/home/worm/${plan.wormMatchId}`).then(orNull) : null,
  ]);
  const heroMatch = state.last_match && state.last_match.id === id ? state.last_match : (worm?.match ?? null);
  return { state, tiles, standings, hero: resolveHero(plan, { wagon, xi, worm }, heroMatch), error: null };
}
