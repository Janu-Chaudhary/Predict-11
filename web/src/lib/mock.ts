import type { PointsRange } from "./range";
import type { Role, TeamCode } from "./tokens";

/** Shape the builder UI expects; will be replaced by the generated API type. */
export type Player = {
  id: string;
  name: string;
  team: TeamCode;
  role: Role;
  credits: number;
  projection: PointsRange;
  captain?: boolean;
  viceCaptain?: boolean;
  /** Headshot URL (official IPL hosts). Missing → initials. */
  photoUrl?: string | null;
};

/** Mock XI for CSK vs MI — placeholder data only, not a prediction. */
export const MOCK_XI: Player[] = [
  { id: "p1", name: "MS Dhoni", team: "CSK", role: "WK", credits: 8.5, projection: { floor: 4, median: 22, ceiling: 58 } },
  { id: "p2", name: "Ruturaj Gaikwad", team: "CSK", role: "BAT", credits: 9.5, projection: { floor: 8, median: 41, ceiling: 96 }, captain: true },
  { id: "p3", name: "Rohit Sharma", team: "MI", role: "BAT", credits: 9.5, projection: { floor: 6, median: 36, ceiling: 102 }, viceCaptain: true },
  { id: "p4", name: "Suryakumar Yadav", team: "MI", role: "BAT", credits: 9.5, projection: { floor: 5, median: 38, ceiling: 110 } },
  { id: "p5", name: "Shivam Dube", team: "CSK", role: "BAT", credits: 8.5, projection: { floor: 3, median: 29, ceiling: 84 } },
  { id: "p6", name: "Ravindra Jadeja", team: "CSK", role: "AR", credits: 9, projection: { floor: 12, median: 37, ceiling: 78 } },
  { id: "p7", name: "Hardik Pandya", team: "MI", role: "AR", credits: 9, projection: { floor: 10, median: 35, ceiling: 88 } },
  { id: "p8", name: "Jasprit Bumrah", team: "MI", role: "BOWL", credits: 9.5, projection: { floor: 14, median: 40, ceiling: 86 } },
  { id: "p9", name: "Matheesha Pathirana", team: "CSK", role: "BOWL", credits: 8.5, projection: { floor: 4, median: 30, ceiling: 74 } },
  { id: "p10", name: "Trent Boult", team: "MI", role: "BOWL", credits: 8.5, projection: { floor: 6, median: 31, ceiling: 76 } },
  { id: "p11", name: "Noor Ahmad", team: "CSK", role: "BOWL", credits: 8, projection: { floor: 5, median: 28, ceiling: 70 } },
];
