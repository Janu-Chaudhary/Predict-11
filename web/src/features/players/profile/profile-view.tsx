"use client";

import { ArrowLeftRight, Columns3, UserX } from "lucide-react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect } from "react";

import { ProfilePageSkeleton } from "@/components/loaders/page-skeletons";
import { PlayerAvatar } from "@/components/player/player-avatar";
import { TeamBadge } from "@/components/player/team-badge";
import { EmptyState } from "@/components/shell/empty-state";
import { TabLinks } from "@/components/shell/tab-links";
import { cn } from "@/lib/utils";

import { PlayerFantasyPanel } from "../../fantasy/player-fantasy";
import { ApiError } from "../api";
import type { ProfileTab } from "../constants";
import { displayName, fmt, fmtDate, photoOf, seasonSpan, teamCode } from "../format";
import { usePlayerProfile } from "../queries";
import { rememberPlayer } from "../recent";
import type { PlayerProfile, StatFilter } from "../types";
import { filterLabel, Panel, QueryError, ScopeSelect } from "../ui";
import { FieldingTab } from "./fielding-tab";
import { OverviewTab } from "./overview-tab";
import { SplitsTab } from "./splits-tab";


/** Bowler if they have bowled more balls than they have faced. Drives tile order and the H2H shortcut. */
export function primarySkill(p: Pick<PlayerProfile, "batting" | "bowling">): "bat" | "bowl" {
  return p.bowling.balls > p.batting.balls ? "bowl" : "bat";
}

export function ProfileView({ id, tab, filter }: { id: string; tab: ProfileTab; filter: StatFilter }) {
  const router = useRouter();
  const pathname = usePathname();
  const q = usePlayerProfile(id, filter);
  const p = q.data;

  useEffect(() => {
    if (p && p.id === id) rememberPlayer({ id: p.id, name: displayName(p), team: p.last_team, image: photoOf(p) });
  }, [p, id]);

  const href = (next: { tab?: ProfileTab; filter?: StatFilter }) => {
    const sp = new URLSearchParams();
    const t = next.tab ?? tab;
    const f = next.filter ?? filter;
    if (t !== "overview") sp.set("tab", t);
    if (f.season) sp.set("season", String(f.season));
    else if (f.since) sp.set("since", f.since);
    return `${pathname}${sp.size ? `?${sp}` : ""}`;
  };

  if (q.isPending) return <ProfilePageSkeleton label="Loading player profile" />;
  if (q.isError) {
    if (q.error instanceof ApiError && q.error.status === 404) {
      return (
        <EmptyState
          icon={UserX}
          title="Player not found"
          why={`No IPL player has the id “${id}”. Player ids come from the Cricsheet registry, so old links can break when a profile is merged.`}
          action={{ href: "/players", label: "Search players" }}
        />
      );
    }
    return <QueryError error={q.error} onRetry={() => q.refetch()} what="this player" />;
  }
  if (!p) return <ProfilePageSkeleton label="Loading player profile" />;

  const code = teamCode(p.last_team);
  const skill = primarySkill(p);
  const h2hHref = skill === "bowl" ? `/h2h?bowler=${encodeURIComponent(p.id)}` : `/h2h?batter=${encodeURIComponent(p.id)}`;
  const empty = p.matches === 0;
  const title = displayName(p);
  const aliases = p.aliases.filter((a) => a !== title && a !== p.name);

  return (
    <div className={cn("transition-opacity", q.isPlaceholderData && "opacity-60")} aria-busy={q.isFetching}>
      <header className="mb-4 flex flex-wrap items-start gap-3 md:mb-6 md:gap-4">
        <PlayerAvatar name={title} src={photoOf(p)} team={code ?? undefined} size="lg" eager />
        <div className="min-w-0 flex-1">
          <p className="text-overline flex items-center gap-1.5 text-muted-foreground">
            {code && <TeamBadge team={code} showCode={false} />}
            <span className="truncate">{p.last_team ?? "IPL player"}</span>
          </p>
          <h1 className="text-display truncate">{title}</h1>
          {title !== p.name && <p className="truncate text-xs text-muted-foreground">Scorecard name: {p.name}</p>}
          {aliases.length > 0 && <p className="truncate text-sm text-muted-foreground">Also known as {aliases.join(", ")}</p>}
          <dl className="num mt-1.5 flex flex-wrap gap-x-4 gap-y-1 text-sm">
            <Meta label="Seasons">
              {seasonSpan(p.seasons)} <span className="text-muted-foreground">({p.seasons.length})</span>
            </Meta>
            <Meta label="Matches">{fmt(p.matches)}</Meta>
            <Meta label="Last match">{fmtDate(p.last_match)}</Meta>
          </dl>
        </div>
        <div className="flex w-full flex-wrap items-center gap-2 sm:w-auto">
          <Link
            href={`/players/compare?ids=${encodeURIComponent(p.id)}`}
            className="inline-flex h-10 items-center gap-1.5 rounded-[10px] border border-border bg-card px-3 text-sm font-medium outline-none hover:bg-surface-2 focus-visible:ring-2 focus-visible:ring-ring"
          >
            <Columns3 aria-hidden className="size-4" /> Compare
          </Link>
          <Link
            href={h2hHref}
            className="inline-flex h-10 items-center gap-1.5 rounded-[10px] border border-border bg-card px-3 text-sm font-medium outline-none hover:bg-surface-2 focus-visible:ring-2 focus-visible:ring-ring"
          >
            <ArrowLeftRight aria-hidden className="size-4" /> H2H
          </Link>
        </div>
      </header>

      <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
        <ScopeSelect value={filter} onChange={(f) => router.replace(href({ filter: f }), { scroll: false })} />
        <p className="text-xs text-muted-foreground" aria-live="polite">
          {q.isFetching ? "Updating…" : `Showing ${filterLabel(filter).toLowerCase()} stats · IPL only`}
        </p>
      </div>

      <TabLinks
        label="Player sections"
        tabs={[
          { key: "overview", label: "Overview" },
          { key: "splits", label: "Splits" },
          { key: "fielding", label: "Fielding" },
        ]}
        active={tab}
        hrefFor={(k) => href({ tab: k as ProfileTab })}
      />

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-12 lg:gap-6">
        <div className="grid grid-cols-1 min-w-0 content-start gap-4 lg:col-span-8">
          {empty ? (
            <EmptyState
              icon={UserX}
              title={`No matches in ${filterLabel(filter)}`}
              why="This player has no IPL appearances in the selected scope."
              action={{ href: href({ filter: {} }), label: "Show career stats" }}
            />
          ) : tab === "overview" ? (
            <OverviewTab p={p} skill={skill} />
          ) : tab === "splits" ? (
            <SplitsTab p={p} skill={skill} />
          ) : (
            <FieldingTab p={p} />
          )}
        </div>
        <aside className="grid grid-cols-1 content-start gap-4 lg:sticky lg:top-20 lg:col-span-4 lg:self-start" aria-label="Player side panel">
          <PlayerFantasyPanel id={p.id} filter={filter} scopeLabel={filterLabel(filter)} />
          <Panel title="Teams" bodyClassName="px-0 md:px-0 pb-1">
            <ul className="divide-y divide-border">
              {p.teams.map((t) => (
                <li key={t.id} className="flex min-h-11 items-center gap-3 px-3 py-1.5 md:px-4">
                  <TeamBadge team={teamCode(t.name) ?? ""} />
                  <span className="min-w-0 flex-1 truncate text-sm">{t.name}</span>
                  <span className="num text-right text-xs text-muted-foreground">
                    {seasonSpan([t.first_season, t.last_season])} · {t.matches} m
                  </span>
                </li>
              ))}
            </ul>
          </Panel>
        </aside>
      </div>
    </div>
  );
}

function Meta({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex items-baseline gap-1.5">
      <dt className="text-xs text-muted-foreground">{label}</dt>
      <dd className="font-medium">{children}</dd>
    </div>
  );
}
