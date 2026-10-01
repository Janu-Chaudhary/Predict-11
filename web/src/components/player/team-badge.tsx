"use client";

import Image from "next/image";
import { useState } from "react";

import { badgesClash, getTeam } from "@/lib/tokens";
import { cn } from "@/lib/utils";

/** Rendered size (px) of the circular badge per size, and of the crest inside it. */
const DIM = {
  sm: { box: 20, img: 16 },
  md: { box: 32, img: 24 },
  lg: { box: 40, img: 30 },
  xl: { box: 56, img: 42 },
} as const;

export type TeamBadgeSize = keyof typeof DIM;

/**
 * Team identity badge (§2.3). Crest from /public/teams on a light disc with a team-colour ring;
 * historical franchises and missing/broken logos fall back to the monogram in team colours.
 * `sm` is an inline pill (crest + code) for rows; `md`+ are circular crests (code is sr-only).
 * Pass `opponent` + `side="away"` in a two-team context to apply the clash rule: a clashing away
 * badge swaps its ring to the secondary colour and dashes it.
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
  const ring = clash ? t.secondary : t.primary;
  const d = DIM[size];
  const withCode = showCode ?? size === "sm";
  const useLogo = Boolean(t.logo) && !broken;

  const disc = useLogo ? (
    <span
      aria-hidden
      className={cn("relative flex shrink-0 items-center justify-center overflow-hidden rounded-full bg-white", clash && "outline-dashed outline-1 outline-offset-1")}
      style={{ width: d.box, height: d.box, boxShadow: `0 0 0 ${size === "sm" ? 1.5 : 2}px ${ring}`, outlineColor: clash ? ring : undefined }}
    >
      <Image
        src={t.logo!}
        alt=""
        width={d.img}
        height={d.img}
        onError={() => setBroken(true)}
        className="object-contain"
        style={{ width: d.img, height: d.img }}
      />
    </span>
  ) : (
    <span
      aria-hidden
      className={cn("font-condensed flex shrink-0 items-center justify-center rounded-full leading-none font-bold", size === "sm" ? "text-[9px]" : size === "md" ? "text-[11px]" : size === "lg" ? "text-[13px]" : "text-base")}
      style={{
        width: d.box,
        height: d.box,
        backgroundColor: t.primary,
        color: t.onPrimary,
        boxShadow: clash ? `0 0 0 2px var(--background), 0 0 0 4px ${ring}` : `inset 0 -2px 0 ${t.secondary}`,
      }}
    >
      {size === "sm" && withCode ? "" : t.short.slice(0, 4)}
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
        withCode && "h-6 gap-1 rounded-full bg-surface-2 py-0.5 pr-2 pl-0.5 ring-1 ring-border ring-inset",
        className,
      )}
    >
      {disc}
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
