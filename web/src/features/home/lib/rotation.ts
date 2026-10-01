import type { HeroKind, HomeMatch, HomeState, ResolvedHero, Wagon, Worm, XI } from "../types";

export type HeroPreview = HeroKind | null;

/** `?hero=A|B|C` forces a concept for preview; anything else is ignored. */
export function parsePreview(raw: string | string[] | undefined): HeroPreview {
  const v = Array.isArray(raw) ? raw[0] : raw;
  return v === "A" || v === "B" || v === "C" ? v : null;
}

export type HeroPlan = {
  requested: HeroKind;
  /** Match whose shot data (A) or XI (B) is wanted. */
  heroMatchId: number | null;
  /** Match for the C worm: the hero match, or the fallback when A/B data is missing. */
  wormMatchId: number | null;
  reason: string;
};

/**
 * What to fetch for the hero (§8 owner decision): B before a match, A after a match when
 * official shot data exists, otherwise C; off-season → C on the season final. The backend
 * already picked `state.hero`; a preview overrides it. The worm is always fetched for
 * C or as the fallback, from the last completed match when the hero match is a fixture.
 */
export function planHero(state: HomeState, preview: HeroPreview = null): HeroPlan {
  const requested = preview ?? state.hero;
  const last = state.last_match?.id ?? null;
  const heroMatchId =
    preview && preview !== state.hero ? (state.hero_match_id ?? last) : state.hero_match_id;
  const fixtureId = state.next_fixture?.id ?? null;
  const wormMatchId = heroMatchId !== null && heroMatchId !== fixtureId ? heroMatchId : last;
  const reason = preview && preview !== state.hero ? `Preview of hero ${preview}.` : state.hero_reason;
  return { requested, heroMatchId, wormMatchId, reason };
}

const FALLBACK_NOTE: Record<"A" | "B", string> = {
  A: "No official shot data for this match yet, so the ball-by-ball worm.",
  B: "Fantasy points and roles are not persisted yet, so the ball-by-ball worm.",
};

/** Pick the hero that can actually be drawn with the data we got back (never invents data). */
export function resolveHero(
  plan: HeroPlan,
  got: { wagon?: Wagon | null; xi?: XI | null; worm?: Worm | null },
  match: HomeMatch | null,
): ResolvedHero {
  if (plan.requested === "A" && got.wagon && got.wagon.shots.length > 0) {
    return { kind: "A", wagon: got.wagon, match, note: plan.reason };
  }
  if (plan.requested === "B" && got.xi && got.xi.players.filter((p) => p.picked).length === 11) {
    return { kind: "B", xi: got.xi, match, note: plan.reason };
  }
  if (got.worm && got.worm.innings.length > 0) {
    const note = plan.requested === "C" ? plan.reason : FALLBACK_NOTE[plan.requested];
    return { kind: "C", worm: got.worm, note };
  }
  return { kind: "none", note: "No ball-by-ball data to draw yet." };
}
