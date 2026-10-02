import { API_URL } from "@/lib/env";

/**
 * Global player search: GET /api/v1/players/search?q=
 * The endpoint is being built in parallel, so the response is parsed defensively and a
 * 404/501/network failure resolves to `{ status: "unavailable" }` instead of throwing.
 */

export type PlayerHit = {
  id: string;
  name: string;
  team?: string;
  role?: string;
  imageUrl?: string;
};

export type PlayerSearchResult =
  | { status: "ok"; hits: PlayerHit[] }
  | { status: "unavailable"; reason: string };

const str = (v: unknown) => (typeof v === "string" && v.trim() ? v.trim() : typeof v === "number" ? String(v) : undefined);

function toHit(raw: unknown): PlayerHit | null {
  if (!raw || typeof raw !== "object") return null;
  const r = raw as Record<string, unknown>;
  const id = str(r.id) ?? str(r.player_id) ?? str(r.key) ?? str(r.slug);
  const name = str(r.display_name) ?? str(r.name) ?? str(r.full_name) ?? str(r.known_as);
  if (!id || !name) return null;
  const team = str(r.team) ?? str(r.team_code) ?? str(r.current_team) ?? str((r.team as Record<string, unknown> | undefined)?.code);
  const role = str(r.role) ?? str(r.playing_role);
  const imageUrl = str(r.image_url);
  return imageUrl ? { id, name, team, role, imageUrl } : { id, name, team, role };
}

/** Accepts `[...]`, `{results|items|players|data|hits: [...]}`. */
export function parsePlayerSearch(body: unknown): PlayerHit[] {
  const list = Array.isArray(body)
    ? body
    : body && typeof body === "object"
      ? (["results", "items", "players", "data", "hits"]
          .map((k) => (body as Record<string, unknown>)[k])
          .find(Array.isArray) as unknown[] | undefined)
      : undefined;
  return (list ?? []).map(toHit).filter((h): h is PlayerHit => h !== null);
}

export async function searchPlayers(q: string, signal?: AbortSignal): Promise<PlayerSearchResult> {
  let res: Response;
  try {
    res = await fetch(`${API_URL}/api/v1/players/search?q=${encodeURIComponent(q)}`, {
      signal,
      headers: { accept: "application/json" },
    });
  } catch (e) {
    if ((e as Error).name === "AbortError") throw e;
    return { status: "unavailable", reason: "The API is unreachable." };
  }
  if (res.status === 404 || res.status === 501 || res.status === 405) {
    return { status: "unavailable", reason: "Player search isn’t live on the API yet." };
  }
  if (!res.ok) return { status: "unavailable", reason: `Search failed (HTTP ${res.status}).` };
  try {
    return { status: "ok", hits: parsePlayerSearch(await res.json()) };
  } catch {
    return { status: "unavailable", reason: "Search returned an unexpected response." };
  }
}

/** Suggestions for the empty ⌘K box: GET /api/v1/players/popular. Failures resolve to []. */
export async function fetchPopularPlayers(signal?: AbortSignal): Promise<PlayerHit[]> {
  try {
    const res = await fetch(`${API_URL}/api/v1/players/popular?limit=6`, { signal, headers: { accept: "application/json" } });
    return res.ok ? parsePlayerSearch(await res.json()) : [];
  } catch (e) {
    if ((e as Error).name === "AbortError") throw e;
    return [];
  }
}
