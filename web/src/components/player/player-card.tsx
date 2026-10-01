"use client";

import { Ban, Lock, LockOpen } from "lucide-react";
import { useId } from "react";

import { Button } from "@/components/ui/button";
import type { Player } from "@/lib/mock";
import { cn } from "@/lib/utils";

import { RangeBar } from "./range-bar";
import { RoleChip } from "./role-chip";
import { TeamBadge } from "./team-badge";

export type PlayerStatus = "locked" | "excluded" | null;

export function PlayerCard({
  player,
  status = null,
  onToggleLock,
  onToggleExclude,
  className,
}: {
  player: Player;
  status?: PlayerStatus;
  onToggleLock?: (id: string) => void;
  onToggleExclude?: (id: string) => void;
  className?: string;
}) {
  const locked = status === "locked";
  const excluded = status === "excluded";
  const headingId = useId();

  return (
    <article
      aria-labelledby={headingId}
      data-status={status ?? "none"}
      className={cn(
        "rounded-xl bg-card p-3 text-card-foreground ring-1 ring-foreground/10 transition-[opacity,box-shadow]",
        locked && "ring-2 ring-pitch",
        excluded && "opacity-60",
        className,
      )}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <h3 id={headingId} className={cn("truncate text-sm font-semibold", excluded && "line-through")}>
            {player.name}
            {player.captain && <span className="ml-1.5 rounded bg-foreground px-1 text-[10px] text-background" aria-label="Captain">C</span>}
            {player.viceCaptain && <span className="ml-1.5 rounded border px-1 text-[10px]" aria-label="Vice-captain">VC</span>}
          </h3>
          <div className="mt-1 flex items-center gap-1.5">
            <TeamBadge team={player.team} />
            <RoleChip role={player.role} />
          </div>
        </div>
        <div className="shrink-0 text-right">
          <div className="text-sm font-semibold tabular-nums">{player.credits.toFixed(1)}</div>
          <div className="text-[10px] text-muted-foreground">credits</div>
        </div>
      </div>

      <div className="mt-3">
        <div className="mb-1 text-[10px] font-medium tracking-wide text-muted-foreground uppercase">Projected pts</div>
        <RangeBar range={player.projection} />
      </div>

      <div className="mt-3 grid grid-cols-2 gap-2">
        <Button
          type="button"
          size="sm"
          variant={locked ? "default" : "outline"}
          aria-pressed={locked}
          aria-label={`${locked ? "Unlock" : "Lock"} ${player.name}`}
          onClick={() => onToggleLock?.(player.id)}
          className={cn("h-9", locked && "bg-pitch text-white hover:bg-pitch/90")}
        >
          {locked ? <Lock aria-hidden /> : <LockOpen aria-hidden />}
          {locked ? "Locked" : "Lock"}
        </Button>
        <Button
          type="button"
          size="sm"
          variant={excluded ? "destructive" : "outline"}
          aria-pressed={excluded}
          aria-label={`${excluded ? "Include" : "Exclude"} ${player.name}`}
          onClick={() => onToggleExclude?.(player.id)}
          className="h-9"
        >
          <Ban aria-hidden />
          {excluded ? "Excluded" : "Exclude"}
        </Button>
      </div>
    </article>
  );
}
