"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";

import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import { cn } from "@/lib/utils";

import { EXPLORE_NAV, MORE_ITEM, PRIMARY_NAV, isActive, isMoreActive, type NavItem } from "./nav-items";

/* ---------------- Desktop rail (≥ 1024 px) ---------------- */

function RailLink({ item, active }: { item: NavItem; active: boolean }) {
  const Icon = item.icon;
  return (
    <Link
      href={item.href}
      aria-current={active ? "page" : undefined}
      className={cn(
        "group relative flex flex-col items-center gap-1 rounded-[10px] px-1 py-2 text-[11px] font-medium text-muted-foreground transition-colors duration-200 outline-none hover:bg-surface-2 hover:text-foreground focus-visible:ring-2 focus-visible:ring-ring",
        "xl:flex-row xl:gap-3 xl:px-3 xl:text-sm",
        active && "bg-surface-2 text-foreground",
      )}
    >
      {active && <span aria-hidden className="absolute top-2 bottom-2 left-0 w-[3px] rounded-full bg-primary xl:top-1.5 xl:bottom-1.5" />}
      <Icon aria-hidden className={cn("size-5", active && "text-gold-text")} strokeWidth={1.75} />
      <span>{item.label}</span>
    </Link>
  );
}

export function SideRail() {
  const pathname = usePathname();
  return (
    <aside className="sticky top-14 hidden h-[calc(100dvh-3.5rem)] w-[72px] shrink-0 border-r border-border lg:block xl:w-60">
      <nav aria-label="Main" className="flex h-full flex-col gap-1 overflow-y-auto p-2 xl:p-3">
        <ul className="flex flex-col gap-1">
          {PRIMARY_NAV.map((item) => (
            <li key={item.href}>
              <RailLink item={item} active={isActive(pathname, item.href)} />
            </li>
          ))}
        </ul>
        <div role="separator" className="mx-2 my-2 h-px bg-border" />
        <p className="text-overline hidden px-3 pb-1 text-faint xl:block">Explore</p>
        <ul className="flex flex-col gap-1">
          {EXPLORE_NAV.map((item) => (
            <li key={item.href}>
              <RailLink item={item} active={isActive(pathname, item.href)} />
            </li>
          ))}
        </ul>
      </nav>
    </aside>
  );
}

/* ---------------- Mobile bottom nav (< 1024 px) ---------------- */

function TabLink({ item, active, onClick }: { item: NavItem; active: boolean; onClick?: () => void }) {
  const Icon = item.icon;
  const isBuild = item.href === "/build";
  const content = (
    <>
      <span
        className={cn(
          "flex h-7 w-12 items-center justify-center rounded-full transition-colors duration-200",
          active && "bg-surface-3",
        )}
      >
        <Icon aria-hidden className={cn("size-5", (active || isBuild) && "text-gold-text")} strokeWidth={1.75} />
      </span>
      {item.label}
    </>
  );
  const cls = cn(
    "flex h-16 w-full flex-col items-center justify-center gap-0.5 text-[11px] font-medium text-muted-foreground outline-none focus-visible:bg-surface-2",
    active && "text-foreground",
  );
  if (onClick) {
    return (
      <button type="button" onClick={onClick} aria-haspopup="dialog" aria-current={active ? "page" : undefined} className={cls}>
        {content}
      </button>
    );
  }
  return (
    <Link href={item.href} aria-current={active ? "page" : undefined} className={cls}>
      {content}
    </Link>
  );
}

export function BottomNav() {
  const pathname = usePathname();
  const [moreOpen, setMoreOpen] = useState(false);
  return (
    <>
      <nav
        aria-label="Main"
        className="glass fixed inset-x-0 bottom-0 z-40 border-t border-border pb-[env(safe-area-inset-bottom)] lg:hidden"
      >
        <ul className="mx-auto grid max-w-lg grid-cols-5">
          {PRIMARY_NAV.map((item) => (
            <li key={item.href}>
              <TabLink item={item} active={isActive(pathname, item.href)} />
            </li>
          ))}
          <li>
            <TabLink item={MORE_ITEM} active={isMoreActive(pathname)} onClick={() => setMoreOpen(true)} />
          </li>
        </ul>
      </nav>
      <Sheet open={moreOpen} onOpenChange={setMoreOpen}>
        <SheetContent side="bottom" className="glass rounded-t-[20px] pb-[calc(env(safe-area-inset-bottom)+1rem)]">
          <SheetHeader>
            <SheetTitle>More</SheetTitle>
            <SheetDescription>Explore teams, players, venues and how accurate the model is.</SheetDescription>
          </SheetHeader>
          <MoreList onNavigate={() => setMoreOpen(false)} className="px-4" />
        </SheetContent>
      </Sheet>
    </>
  );
}

/** Explore links as large rows. Used by the More sheet and the /more page. */
export function MoreList({ onNavigate, className }: { onNavigate?: () => void; className?: string }) {
  const pathname = usePathname();
  return (
    <ul className={cn("grid gap-1 sm:grid-cols-2", className)}>
      {EXPLORE_NAV.map((item) => {
        const Icon = item.icon;
        const active = isActive(pathname, item.href);
        return (
          <li key={item.href}>
            <Link
              href={item.href}
              onClick={onNavigate}
              aria-current={active ? "page" : undefined}
              className={cn(
                "flex min-h-[52px] items-center gap-3 rounded-[10px] px-3 py-2 outline-none hover:bg-surface-2 focus-visible:ring-2 focus-visible:ring-ring",
                active && "bg-surface-2",
              )}
            >
              <span className="flex size-9 items-center justify-center rounded-lg bg-surface-2 text-muted-foreground">
                <Icon aria-hidden className="size-5" strokeWidth={1.75} />
              </span>
              <span className="min-w-0">
                <span className="block text-sm font-medium">{item.label}</span>
                {item.description && <span className="block truncate text-xs text-muted-foreground">{item.description}</span>}
              </span>
            </Link>
          </li>
        );
      })}
    </ul>
  );
}
