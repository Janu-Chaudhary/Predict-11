"use client";

import { ArrowLeftRight, Swords } from "lucide-react";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { HeaderSkeleton, RowsSkeleton, TilesSkeleton } from "@/components/loaders/page-skeletons";
import { EmptyState } from "@/components/shell/empty-state";
import { PageHeader } from "@/components/shell/page-header";
import { cn } from "@/lib/utils";

import { PlayerPicker, type PickedPlayer } from "../players/player-picker";
import { QueryError } from "../players/ui";
import { DEFAULT_PAIR } from "./constants";
import { H2HCard } from "./h2h-card";
import { MatchupList } from "./matchup-list";
import { useH2H, type H2HQuery } from "./queries";


export function h2hHref(q: H2HQuery): string {
  const sp = new URLSearchParams();
  if (q.batter) sp.set("batter", q.batter);
  if (q.bowler) sp.set("bowler", q.bowler);
  if (q.since) sp.set("since", q.since);
  return `/h2h${sp.size ? `?${sp}` : ""}`;
}

const SINCE_OPTIONS = [
  { value: "", label: "All IPL" },
  { value: "2024", label: "Since 2024" },
  { value: "2023", label: "Impact-sub era (2023+)" },
  { value: "2018", label: "Since 2018" },
];

export function H2HView({ query }: { query: H2HQuery }) {
  const router = useRouter();
  const q = useH2H(query);
  const data = q.data;
  // Names picked in this session, so pickers show a name before the response lands.
  const [picked, setPicked] = useState<Record<string, PickedPlayer>>({});

  const go = (next: H2HQuery) => router.replace(h2hHref(next), { scroll: false });
  const pending = q.isPending || q.isPlaceholderData ? "Loading…" : "Unknown player";
  const batterVal: PickedPlayer | null = query.batter ? (picked[query.batter] ?? (data?.batter?.id === query.batter ? data.batter : { id: query.batter, name: pending })) : null;
  const bowlerVal: PickedPlayer | null = query.bowler ? (picked[query.bowler] ?? (data?.bowler?.id === query.bowler ? data.bowler : { id: query.bowler, name: pending })) : null;

  const choose = (role: "batter" | "bowler", p: PickedPlayer | null) => {
    if (p) setPicked((m) => ({ ...m, [p.id]: p }));
    go({ ...query, [role]: p?.id });
  };

  return (
    <>
      <PageHeader
        overline="Head-to-head"
        title="Batter v bowler"
        subtitle="Every IPL ball between two players, with a confidence badge for how much the sample can tell you."
      />

      <div className="mb-4 grid items-end gap-3 rounded-xl border border-border bg-card p-3 shadow-e1 md:grid-cols-[1fr_auto_1fr_auto] md:p-4">
        <PlayerPicker label="Batter" placeholder="Search a batter…" value={batterVal} onChange={(p) => choose("batter", p)} exclude={query.bowler ? [query.bowler] : []} />
        <button
          type="button"
          onClick={() => go({ ...query, batter: query.bowler, bowler: query.batter })}
          disabled={!query.batter && !query.bowler}
          aria-label="Swap batter and bowler"
          className="inline-flex h-11 items-center justify-center gap-1.5 justify-self-center rounded-[10px] px-3 text-sm text-muted-foreground outline-none hover:bg-surface-2 hover:text-foreground focus-visible:ring-2 focus-visible:ring-ring disabled:opacity-40"
        >
          <ArrowLeftRight aria-hidden className="size-4" />
          <span className="md:sr-only">Swap</span>
        </button>
        <PlayerPicker label="Bowler" placeholder="Search a bowler…" value={bowlerVal} onChange={(p) => choose("bowler", p)} exclude={query.batter ? [query.batter] : []} />
        <label className="grid gap-1.5">
          <span className="text-overline text-muted-foreground">Period</span>
          <select
            value={query.since ?? ""}
            onChange={(e) => go({ ...query, since: e.target.value || undefined })}
            className="num h-11 rounded-[10px] border border-input bg-card px-2.5 text-sm outline-none focus-visible:ring-2 focus-visible:ring-ring"
          >
            {SINCE_OPTIONS.map((o) => (
              <option key={o.value} value={o.value}>
                {o.label}
              </option>
            ))}
          </select>
        </label>
      </div>

      {!query.batter && !query.bowler ? (
        <EmptyState
          icon={Swords}
          title="Pick a batter, a bowler, or both"
          why="One player shows their toughest (or easiest) opponents; two players show every ball between them."
          action={{ href: h2hHref(DEFAULT_PAIR), label: "Try V Kohli v JJ Bumrah" }}
        />
      ) : q.isError ? (
        <QueryError error={q.error} onRetry={() => q.refetch()} what="the head-to-head" />
      ) : q.isPending || !data ? (
        <div role="status" aria-busy="true" aria-label="Loading head-to-head" className="grid grid-cols-1 gap-4 lg:grid-cols-12">
          <div className="lg:col-span-8">
            <HeaderSkeleton />
            <TilesSkeleton />
          </div>
          <RowsSkeleton rows={6} className="lg:col-span-4" />
        </div>
      ) : (
        <div className={cn("grid grid-cols-1 gap-4 transition-opacity lg:grid-cols-12 lg:gap-6", q.isPlaceholderData && "opacity-60")} aria-busy={q.isFetching}>
          <div className="grid grid-cols-1 min-w-0 content-start gap-4 lg:col-span-8">
            {data.batter && data.bowler ? (
              data.pair && data.pair.balls > 0 ? (
                <H2HCard batter={data.batter} bowler={data.bowler} pair={data.pair} />
              ) : (
                <EmptyState
                  icon={Swords}
                  title={`${data.batter.name} has never faced ${data.bowler.name}`}
                  why={`No IPL deliveries between them${query.since ? ` since ${query.since}` : ""}. The lists alongside show who each of them has met most.`}
                  action={query.since ? { href: h2hHref({ ...query, since: undefined }), label: "Try all IPL seasons" } : undefined}
                />
              )
            ) : (
              <p className="rounded-xl border border-dashed border-border bg-card/60 p-4 text-sm text-muted-foreground">
                Pick a {data.batter ? "bowler" : "batter"} to see every ball between the two, or open a name from the list.
              </p>
            )}
            {data.notes.length > 0 && (
              <ul className="text-xs text-muted-foreground">
                {data.notes.map((n) => (
                  <li key={n}>{n}</li>
                ))}
              </ul>
            )}
          </div>
          <div className="grid grid-cols-1 min-w-0 content-start gap-4 lg:col-span-4">
            {data.batter && (
              <MatchupList
                title={`Toughest bowlers for ${data.batter.name}`}
                subtitle={`Most dismissals, min ${data.min_balls} balls`}
                rows={data.top_bowlers_vs_batter}
                activeId={query.bowler}
                hrefFor={(r) => h2hHref({ ...query, bowler: r.player.id })}
                empty={`No bowler has bowled ${data.min_balls}+ balls to ${data.batter.name} in this period.`}
              />
            )}
            {data.bowler && (
              <MatchupList
                title={`Batters who dominate ${data.bowler.name}`}
                subtitle={`Most runs, min ${data.min_balls} balls`}
                rows={data.top_batters_vs_bowler}
                activeId={query.batter}
                hrefFor={(r) => h2hHref({ ...query, batter: r.player.id })}
                empty={`No batter has faced ${data.min_balls}+ balls from ${data.bowler.name} in this period.`}
              />
            )}
          </div>
        </div>
      )}
    </>
  );
}
