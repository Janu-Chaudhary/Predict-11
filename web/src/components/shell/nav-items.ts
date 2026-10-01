import { BarChart3, CalendarDays, ClipboardCheck, Shirt, type LucideIcon } from "lucide-react";

export type NavItem = { href: string; label: string; icon: LucideIcon };

export const NAV_ITEMS: NavItem[] = [
  { href: "/", label: "Fixtures", icon: CalendarDays },
  { href: "/builder", label: "Builder", icon: Shirt },
  { href: "/review", label: "Review", icon: ClipboardCheck },
  { href: "/accuracy", label: "Accuracy", icon: BarChart3 },
];

export function isActive(pathname: string, href: string) {
  return href === "/" ? pathname === "/" : pathname === href || pathname.startsWith(`${href}/`);
}
