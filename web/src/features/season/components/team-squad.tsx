"use client";

import { Plane } from "lucide-react";
import Link from "next/link";

import { RowsSkeleton } from "@/components/loaders/page-skeletons";
import { PlayerAvatar } from "@/components/player/player-avatar";
import { RoleChip } from "@/components/player/role-chip";
import { SectionHeader } from "@/components/shell/page-header";
import { cn } from "@/lib/utils";

import { displayName, photoOf } from "../../players/format";
import { useTeamSquad } from "../queries";
import type { SquadPlayer, TeamSummary } from "../types";
import { ErrorState } from "./states";

const GROUPS = [
  { role: "BAT", title: "Batters" },
  { role: "WK", title: "Wicket-keepers" },
  { role: "AR", title: "All-rounders" },
  { role: "BOWL", title: "Bowlers" },
] as const;

function SquadCard({ p, season, team }: { p: SquadPlayer; season: number; team: string }) {
  const name = displayName(p.player);
  const benched = p.matches === 0;
  return (
    <li>
      <Link
        href={`/players/${encodeURIComponent(p.player.id)}`}
        className="group flex h-full flex-col items-center rounded-xl px-2 pt-2 pb-3 text-center outline-none transition-colors hover:bg-surface-2 focus-visible:ring-2 focus-visible:ring-ring"
      >
        <PlayerAvatar name={name} src={photoOf(p.player)} team={team} size="2xl" className={cn("transition-transform duration-200 group-hover:scale-[1.03] motion-reduce:transition-none", benched && "opacity-70")} />
        <span className="mt-2 flex max-w-full items-center gap-1 text-sm leading-5 font-semibold">
          <span className="truncate">{name}</span>
          {p.overseas && (
            <span title="Overseas player" className="shrink-0 text-muted-foreground">
              <Plane aria-hidden className="size-3.5" />
              <span className="sr-only">(overseas)</span>
            </span>
          )}
        </span>
        <span className="mt-1 flex flex-wrap items-center justify-center gap-1.5">
          <RoleChip role={p.role} showIcon={false} />
          {p.credits !== null && <span className="num text-xs text-muted-foreground">{p.credits.toFixed(1)} cr</span>}
        </span>
        <span className="num mt-1 text-xs text-muted-foreground">
          {benched ? <>Didn’t play {season}</> : <>{p.matches} {p.matches === 1 ? "match" : "matches"} in {season}</>}
        </span>
      </Link>
    </li>
  );
}

/** Squad tab: the latest season's roster grouped by role, frameless cut-outs. */
export function TeamSquadView({ team }: { team: TeamSummary }) {
  const q = useTeamSquad(team.id);
  if (q.isPending) return <RowsSkeleton rows={6} />;
  if (q.isError) return <ErrorState title="Couldn't load the squad" error={q.error} onRetry={() => q.refetch()} />;
  const d = q.data;
  const overseas = d.players.filter((p) => p.overseas).length;
  return (
    <div className="mt-4 space-y-6">
      <p className="text-sm text-muted-foreground">
        IPL <span className="num">{d.season}</span> squad · <span className="num">{d.players.length}</span> players
        {overseas > 0 && (
          <>
            {" "}
            · <span className="num">{overseas}</span> overseas
          </>
        )}
        {d.credits_season !== null && d.credits_season !== d.season && (
          <> · credits and squad list from {d.credits_season}; players who didn’t feature in {d.season} are marked</>
        )}
      </p>
      {GROUPS.map((g) => {
        const rows = d.players.filter((p) => p.role === g.role);
        if (rows.length === 0) return null;
        return (
          <section key={g.role} aria-labelledby={`squad-${g.role}`}>
            <SectionHeader id={`squad-${g.role}`} title={`${g.title} (${rows.length})`} />
            <ul className="grid grid-cols-2 gap-3 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6">
              {rows.map((p) => (
                <SquadCard key={p.player.id} p={p} season={d.season} team={team.short_code} />
              ))}
            </ul>
          </section>
        );
      })}
    </div>
  );
}
