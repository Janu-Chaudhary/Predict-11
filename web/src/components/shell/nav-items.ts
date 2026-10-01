import {
  ArrowLeftRight,
  CalendarDays,
  Ellipsis,
  House,
  ListOrdered,
  MapPin,
  Shield,
  Shirt,
  Sparkles,
  Target,
  Trophy,
  Users,
  type LucideIcon,
} from "lucide-react";

export type NavItem = { href: string; label: string; icon: LucideIcon; description?: string };

/** Primary destinations (§3.2): bottom nav on mobile, top group of the desktop rail. */
export const PRIMARY_NAV: NavItem[] = [
  { href: "/", label: "Home", icon: House, description: "Next match, your XI, table snippet" },
  { href: "/matches", label: "Matches", icon: CalendarDays, description: "Fixtures and results" },
  { href: "/build", label: "Build", icon: Shirt, description: "Fantasy XI builder" },
  { href: "/table", label: "Table", icon: ListOrdered, description: "Points table and scenarios" },
];

/** Explore destinations: in the "More" sheet on mobile, below the divider on the rail. */
export const EXPLORE_NAV: NavItem[] = [
  { href: "/teams", label: "Teams", icon: Shield, description: "Squads, fixtures, team stats" },
  { href: "/players", label: "Players", icon: Users, description: "Profiles, form, matchups" },
  { href: "/fantasy", label: "Fantasy", icon: Sparkles, description: "Dream11 leaderboards, consistency, best XIs" },
  { href: "/h2h", label: "H2H", icon: ArrowLeftRight, description: "Team vs team, batter vs bowler" },
  { href: "/venues", label: "Venues", icon: MapPin, description: "Par scores, pace/spin, dew" },
  { href: "/records", label: "Records", icon: Trophy, description: "All-time and season records" },
  { href: "/accuracy", label: "Accuracy", icon: Target, description: "Backtest and calibration" },
];

export const MORE_ITEM: NavItem = { href: "/more", label: "More", icon: Ellipsis };

export const ALL_NAV: NavItem[] = [...PRIMARY_NAV, ...EXPLORE_NAV];

export function isActive(pathname: string, href: string) {
  return href === "/" ? pathname === "/" : pathname === href || pathname.startsWith(`${href}/`);
}

/** "More" is active on /more and on every explore destination. */
export function isMoreActive(pathname: string) {
  return isActive(pathname, MORE_ITEM.href) || EXPLORE_NAV.some((i) => isActive(pathname, i.href));
}
