/**
 * Local types for GET /api/v1/milestones and /api/v1/streaks.
 * Mirrors `backend/src/p11/analytics/players_models.py` (Milestone*, Streak*).
 */
import type { PlayerRef } from "@/features/venues/types";

export type { PlayerRef };

export type MilestoneStat = "runs" | "wickets" | "sixes" | "catches" | "matches";

export type Milestone = {
  player: PlayerRef;
  team: string | null;
  /** Known values are MilestoneStat; kept open so a new stat from the API still renders. */
  stat: MilestoneStat | (string & {});
  current: number;
  target: number;
  needed: number;
  /** e.g. "KH Pandya needs 18 for 2,000 IPL runs" */
  text: string;
};

export type MilestonesResponse = {
  season: number;
  as_of: string | null;
  milestones: Milestone[];
};

export type StreakType = "score30" | "wicket" | "no_duck";

export type StreakEntry = {
  player: PlayerRef;
  team: string | null;
  length: number;
  start_date: string;
  end_date: string;
  /** Streak still running at the end of the scope. */
  active: boolean;
};

export type StreakBoard = {
  type: StreakType | (string & {});
  label: string;
  current: StreakEntry[];
  longest: StreakEntry[];
};

export type StreaksResponse = {
  season: number | null;
  as_of: string | null;
  boards: StreakBoard[];
};
