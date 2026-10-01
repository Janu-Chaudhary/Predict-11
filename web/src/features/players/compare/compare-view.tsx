"use client";

import { Columns3, X } from "lucide-react";
import { useRouter } from "next/navigation";

import { HeaderSkeleton, TableSkeleton } from "@/components/loaders/page-skeletons";
import { TeamBadge } from "@/components/player/team-badge";
import { EmptyState } from "@/components/shell/empty-state";
import { PageHeader } from "@/components/shell/page-header";
import { cn } from "@/lib/utils";

import { MAX_COMPARE } from "../constants";
import { teamCode } from "../format";
import { PlayerPicker } from "../player-picker";
import { usePlayerCompare } from "../queries";
import type { StatFilter } from "../types";
import { filterLabel, QueryError, ScopeSelect } from "../ui";
import { CompareTable } from "./compare-table";


export function compareHref(ids: string[], f: StatFilter): string {
  const sp = new URLSearchParams();
  if (ids.length) sp.set("ids", ids.join(","));
  if (f.season) sp.set("season", String(f.season));
  else if (f.since) sp.set("since", f.since);
  // Keep commas readable in the shareable URL.
  return `/players/compare${sp.size ? `?${sp.toString().replace(/%2C/g, ",")}` : ""}`;
}

export function CompareView({ ids, filter }: { ids: string[]; filter: StatFilter }) {
  const router = useRouter();
  const q = usePlayerCompare(ids, filter);
  const go = (nextIds: string[], f: StatFilter = filter) => router.replace(compareHref(nextIds, f), { scroll: false });
  const players = q.data?.players ?? [];
  // Keep the URL order (the API may reorder).
  const ordered = ids.map((id) => players.find((p) => p.id === id)).filter((p) => p !== undefined);

  return (
    <>
      <PageHeader
        overline="Players"
        title="Compare players"
        subtitle="Up to three players, same scope, same rows. The best value in each row is marked."
        actions={<ScopeSelect value={filter} onChange={(f) => go(ids, f)} />}
      />

      <div className="mb-4 grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {ids.map((id) => {
          const p = ordered.find((x) => x.id === id);
          return (
            <div key={id} className="flex h-11 items-center gap-2 rounded-[10px] border border-border bg-card pr-1 pl-2">
              {p?.last_team ? <TeamBadge team={teamCode(p.last_team) ?? ""} /> : <span aria-hidden className="h-6 w-9 rounded-full bg-surface-3" />}
              <span className="min-w-0 flex-1 truncate text-sm font-semibold">{p?.name ?? id}</span>
              <button
                type="button"
                onClick={() => go(ids.filter((x) => x !== id))}
                aria-label={`Remove ${p?.name ?? id} from comparison`}
                className="inline-flex size-9 items-center justify-center rounded-lg text-muted-foreground outline-none hover:bg-surface-2 hover:text-foreground focus-visible:ring-2 focus-visible:ring-ring"
              >
                <X aria-hidden className="size-4" />
              </button>
            </div>
          );
        })}
        {ids.length < MAX_COMPARE && (
          <PlayerPicker
            label={ids.length === 0 ? "First player" : "Add a player"}
            hideLabel
            placeholder={ids.length === 0 ? "Search the first player…" : "Add a player to compare…"}
            value={null}
            exclude={ids}
            onChange={(p) => p && go([...ids, p.id])}
          />
        )}
      </div>

      {ids.length === 0 ? (
        <EmptyState
          icon={Columns3}
          title="Pick two or three players"
          why="Search above to add players. Each gets a column with the same batting, bowling, fielding and phase rows."
          action={{ href: compareHref(["ba607b88", "740742ef"], {}), label: "Try V Kohli vs RG Sharma" }}
        />
      ) : q.isPending ? (
        <div role="status" aria-busy="true" aria-label="Loading comparison">
          <HeaderSkeleton />
          <TableSkeleton rows={14} cols={ids.length + 1} />
        </div>
      ) : q.isError ? (
        <QueryError error={q.error} onRetry={() => q.refetch()} what="the comparison" />
      ) : (
        <div className={cn("transition-opacity", q.isPlaceholderData && "opacity-60")} aria-busy={q.isFetching}>
          {ids.length === 1 && <p className="mb-3 text-sm text-muted-foreground">Add at least one more player to see who leads each row.</p>}
          <CompareTable players={ordered} caption={`Player comparison, ${filterLabel(filter).toLowerCase()}`} />
        </div>
      )}
    </>
  );
}
