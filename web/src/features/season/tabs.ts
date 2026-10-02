/** Tab ids shared by server pages (URL parsing) and client views. Plain module: no "use client". */
export const SEASON_TABS = ["table", "scenarios", "story"] as const;
export type SeasonTab = (typeof SEASON_TABS)[number];

export const TEAM_TABS = ["overview", "squad", "matches", "h2h"] as const;
export type TeamTab = (typeof TEAM_TABS)[number];

export function parseTab<T extends string>(value: string | string[] | undefined, tabs: readonly T[], fallback: T): T {
  const v = Array.isArray(value) ? value[0] : value;
  return (tabs as readonly string[]).includes(v ?? "") ? (v as T) : fallback;
}
