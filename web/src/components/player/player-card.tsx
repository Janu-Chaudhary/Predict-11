"use client";

import { Ban, Lock, LockOpen } from "lucide-react";
import { useId } from "react";

import { Button } from "@/components/ui/button";
import type { Player } from "@/lib/mock";
import { cn } from "@/lib/utils";

import { RangeBar } from "./range-bar";
import { RoleChip } from "./role-chip";
import { CaptainRoundel } from "./captain-roundel";
import { PlayerAvatar } from "./player-avatar";
import { TeamBadge, TeamStripe } from "./team-badge";

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
        "relative flex gap-3 overflow-hidden rounded-xl border border-border bg-card p-3 text-card-foreground shadow-e1 transition-[opacity,box-shadow] duration-200",
        locked && "ring-2 ring-primary",
        excluded && "opacity-60",
        className,
      )}
    >
      <TeamStripe team={player.team} className="-my-3 -ml-3 rounded-none" />
      <div className="min-w-0 flex-1">
        <div className="flex items-start justify-between gap-2">
          <PlayerAvatar
            name={player.name}
            src={player.photoUrl}
            team={player.team}
            size="md"
          />
          <div className="min-w-0 flex-1">
            <h3
              id={headingId}
              className={cn(
                "truncate text-sm font-semibold",
                excluded && "line-through",
              )}
            >
              {player.name}
              {player.captain && (
                <CaptainRoundel kind="C" className="ml-1.5 align-[-3px]" />
              )}
              {player.viceCaptain && (
                <CaptainRoundel kind="VC" className="ml-1.5 align-[-3px]" />
              )}
            </h3>
            <div className="mt-1 flex items-center gap-1.5">
              <TeamBadge team={player.team} />
              <RoleChip role={player.role} />
            </div>
          </div>
          <div className="shrink-0 text-right">
            <div className="num text-sm font-semibold">
              {player.credits.toFixed(1)}
            </div>
            <div className="text-[11px] text-muted-foreground">credits</div>
          </div>
        </div>

        <div className="mt-3">
          <div className="text-overline mb-1.5 text-muted-foreground">
            Projected pts
          </div>
          <RangeBar range={player.projection} />
        </div>

        <div className="mt-3 grid grid-cols-2 gap-2">
          <Button
            type="button"
            size="sm"
            variant="outline"
            aria-pressed={locked}
            aria-label={`${locked ? "Unlock" : "Lock"} ${player.name}`}
            onClick={() => onToggleLock?.(player.id)}
            className={cn(
              "h-10 rounded-[10px]",
              locked && "border-primary text-gold-text",
            )}
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
            className="h-10 rounded-[10px]"
          >
            <Ban aria-hidden />
            {excluded ? "Excluded" : "Exclude"}
          </Button>
        </div>
      </div>
    </article>
  );
}
