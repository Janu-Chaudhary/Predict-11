/** Plain constants shared by server pages and client views (must not live in "use client" modules). */
export const PROFILE_TABS = ["overview", "splits", "fielding"] as const;
export type ProfileTab = (typeof PROFILE_TABS)[number];

export const MAX_COMPARE = 3;
