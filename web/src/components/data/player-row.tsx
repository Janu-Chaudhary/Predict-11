import Link from "next/link";
import type { ReactNode } from "react";

import { CaptainRoundel } from "@/components/player/captain-roundel";
import { PlayerAvatar } from "@/components/player/player-avatar";
import { RoleChip } from "@/components/player/role-chip";
import { TeamBadge, TeamStripe } from "@/components/player/team-badge";
import type { Role } from "@/lib/tokens";
import { cn } from "@/lib/utils";

export type PlayerRowData = {
  id: string;
  name: string;
  team: string;
  role?: Role;
  captain?: boolean;
  viceCaptain?: boolean;
  /** Headshot URL; falls back to initials. */
  photoUrl?: string | null;
};

/**
 * The same player row everywhere (§1.7): 3 px team stripe · avatar · name · team badge · role chip · key stat.
 * 52 px tall (touch). Links through to the profile unless `href={null}`.
 */
export function PlayerRow({
  player,
  stat,
  meta,
  trailing,
  href,
  className,
}: {
  player: PlayerRowData;
  /** Primary stat, right-aligned and tabular (weight carries emphasis, not colour). */
  stat?: { value: ReactNode; label?: string };
  /** Secondary line under the name (e.g. "9.0 cr · 31% own"). */
  meta?: ReactNode;
  /** Extra right-side content (form strip, range bar, actions). */
  trailing?: ReactNode;
  href?: string | null;
  className?: string;
}) {
  const link = href === undefined ? `/players/${encodeURIComponent(player.id)}` : href;
  const inner = (
    <>
      <TeamStripe team={player.team} className="my-2" />
      <PlayerAvatar name={player.name} src={player.photoUrl} team={player.team} size="sm" />
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-1.5">
          <span className="truncate text-sm font-medium">{player.name}</span>
          {player.captain && <CaptainRoundel kind="C" />}
          {player.viceCaptain && <CaptainRoundel kind="VC" />}
        </div>
        {meta && <div className="num truncate text-xs text-muted-foreground">{meta}</div>}
      </div>
      <TeamBadge team={player.team} />
      {player.role && <RoleChip role={player.role} className="max-sm:hidden" />}
      {trailing}
      {stat && (
        <div className="w-14 shrink-0 text-right">
          <div className="num text-sm font-semibold">{stat.value}</div>
          {stat.label && <div className="text-[11px] leading-4 text-muted-foreground">{stat.label}</div>}
        </div>
      )}
    </>
  );
  const cls = cn("flex min-h-[52px] items-center gap-3 px-3 py-1.5", className);
  return link ? (
    <Link href={link} className={cn(cls, "outline-none hover:bg-surface-2 focus-visible:bg-surface-2 focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-inset")}>
      {inner}
    </Link>
  ) : (
    <div className={cls}>{inner}</div>
  );
}
