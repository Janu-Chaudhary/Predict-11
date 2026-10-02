"use client";

import Image from "next/image";
import { useState } from "react";

import { badgesClash, getTeam } from "@/lib/tokens";
import { cn } from "@/lib/utils";

/** Rendered box (px) per size; the crest is fitted (contain) inside it. */
const DIM = { sm: 20, md: 32, lg: 44, xl: 64, "2xl": 96 } as const;

export type TeamBadgeSize = keyof typeof DIM;

/**
 * Team identity mark (§2.3, owner redesign 2026-10-02): the official transparent crest from
 * /public/teams drawn bare on the page background (no disc, ring or tile). Historical
 * franchises and missing/broken logos show the short code as a monogram in the team colour.
 * `sm` adds the code next to the crest for rows; `md`+ show the crest alone (code is sr-only).
 * `opponent` + `side="away"` still flag a colour clash (`data-clash`) for two-team contexts.
 */
export function TeamBadge({
  team,
  size = "sm",
  opponent,
  side = "home",
  showCode,
  className,
}: {
  team: string;
  size?: TeamBadgeSize;
  opponent?: string;
  side?: "home" | "away";
  /** Show the code next to the crest (default: only for `sm`). */
  showCode?: boolean;
  className?: string;
}) {
  const t = getTeam(team);
  const [broken, setBroken] = useState(false);
  const clash = Boolean(opponent && side === "away" && badgesClash(opponent, team));
  const d = DIM[size];
  const withCode = showCode ?? size === "sm";
  const useLogo = Boolean(t.logo) && !broken;

  const mark = useLogo ? (
    <Image
      aria-hidden
      src={t.logo!}
      alt=""
      width={d}
      height={d}
      onError={() => setBroken(true)}
      className="shrink-0 object-contain"
      style={{ width: d, height: d }}
    />
  ) : withCode && size === "sm" ? null : (
    <span
      aria-hidden
      className="font-condensed flex shrink-0 items-center justify-center leading-none font-bold tracking-tight text-[var(--mono-l)] dark:text-[var(--mono-d)]"
      style={{ width: d, height: d, fontSize: Math.max(10, Math.round(d * 0.36)), ["--mono-l" as string]: t.chartLight, ["--mono-d" as string]: t.chartDark }}
    >
      {t.short.slice(0, 4)}
    </span>
  );

  return (
    <span
      role="img"
      title={t.name}
      aria-label={t.name}
      data-clash={clash || undefined}
      data-historical={t.historical || undefined}
      className={cn(
        "inline-flex shrink-0 items-center",
        withCode && "gap-1",
        className,
      )}
    >
      {mark}
      {withCode ? (
        <span aria-hidden className="font-condensed text-[11px] leading-none font-bold tracking-wide text-foreground">
          {t.short}
        </span>
      ) : (
        <span className="sr-only">{t.short}</span>
      )}
    </span>
  );
}

/** 3 px team stripe for the left edge of match/player rows. */
export function TeamStripe({ team, className }: { team: string; className?: string }) {
  return (
    <span
      aria-hidden
      className={cn("w-[3px] shrink-0 self-stretch rounded-full", className)}
      style={{ backgroundColor: getTeam(team).primary }}
    />
  );
}
