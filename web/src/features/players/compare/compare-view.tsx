"use client";

import { Columns3, LayoutDashboard, Sparkles, Swords } from "lucide-react";
import { useRouter } from "next/navigation";
import type { CSSProperties } from "react";

import { BallIcon, BatIcon, GlovesIcon } from "@/components/icons/cricket";
import { EmptyState } from "@/components/shell/empty-state";
import { PageHeader } from "@/components/shell/page-header";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";

import { ApiError } from "../api";
import { displayName, teamCode } from "../format";
import type { PlayerProfile, StatFilter } from "../types";
import { filterLabel, QueryError, ScopeSelect } from "../ui";
import { playerColours, shortNames } from "./colours";
import { ACCENT, MetricCard } from "./compare-ui";
import { useFantasies, useMatchups, useProfiles } from "./data";
import { FaceOff } from "./face-off";
import { FantasyCompare } from "./fantasy-compare";
import { rowsFor, tally, visibleRows, type Subject } from "./metrics";
import { SeasonChart } from "./season-chart";
import { SkillRadar } from "./skill-radar";

export function compareHref(ids: string[], f: StatFilter): string {
  const sp = new URLSearchParams();
  if (ids.length) sp.set("ids", ids.join(","));
  if (f.season) sp.set("season", String(f.season));
  else if (f.since) sp.set("since", f.since);
  // Keep commas readable in the shareable URL.
  return `/players/compare${sp.size ? `?${sp.toString().replace(/%2C/g, ",")}` : ""}`;
}

/** Each player's colour as `--pc<i>`, switching between the light and dark team chart colour. */
const PC_CLASSES =
  "[--pc0:var(--pc0-l)] [--pc1:var(--pc1-l)] [--pc2:var(--pc2-l)] dark:[--pc0:var(--pc0-d)] dark:[--pc1:var(--pc1-d)] dark:[--pc2:var(--pc2-d)]";

export function CompareView({ ids, filter }: { ids: string[]; filter: StatFilter }) {
  const router = useRouter();
  const go = (nextIds: string[], f: StatFilter = filter) => router.replace(compareHref(nextIds, f), { scroll: false });

  const profileQs = useProfiles(ids, filter);
  const fantasyQs = useFantasies(ids, filter);
  const profiles = profileQs.map((q) => q.data as PlayerProfile | undefined);
  const matchups = useMatchups(profiles, filter);

  const failed = profileQs.map((q) => q.isError && q.error instanceof ApiError && q.error.status === 404);
  const live = ids.flatMap((id, i) => (profiles[i] && !failed[i] ? [{ i, p: profiles[i]! }] : []));
  const subjects: Subject[] = live.map(({ i, p }) => ({
    ...p,
    seasons: p.seasons,
    fantasy: fantasyQs[i].data ?? null,
    vsTypes: matchups.bat[i].data ?? null,
    vsHands: matchups.bowl[i].data ?? null,
  }));
  const names = shortNames(subjects.map((s) => displayName(s)));
  // Colours follow the players actually shown (in URL order).
  const colours = playerColours(live.map(({ p }) => teamCode(p.last_team)));
  const style = Object.fromEntries(colours.flatMap((c, i) => [[`--pc${i}-l`, c.light], [`--pc${i}-d`, c.dark]])) as CSSProperties;

  const pending = profileQs.some((q) => q.isPending);
  const hardError = profileQs.find((q) => q.isError && !(q.error instanceof ApiError && q.error.status === 404));
  const stale = profileQs.some((q) => q.isPlaceholderData);
  const scope = filterLabel(filter);

  const sections = {
    overview: visibleRows(subjects, rowsFor(["Overview"])),
    batting: visibleRows(subjects, rowsFor(["Batting"])),
    bowling: visibleRows(subjects, rowsFor(["Bowling"])),
    fielding: visibleRows(subjects, rowsFor(["Fielding"])),
    fantasy: visibleRows(subjects, rowsFor(["Fantasy"])),
    splits: visibleRows(subjects, rowsFor(["Batting by phase", "Bowling by phase", "Matchups"])),
  };
  // Overall tally skips the Overview duplicates (runs / wickets / dismissals / fantasy mean).
  const totalRows = [...sections.overview.filter((r) => !r.key.startsWith("ov_")), ...sections.batting, ...sections.bowling, ...sections.fielding, ...sections.fantasy, ...sections.splits];
  const total = subjects.length >= 2 ? tally(totalRows, subjects) : null;

  const slotNames = ids.map((id, i) => {
    const k = live.findIndex((x) => x.i === i);
    return k >= 0 ? names[k] : id;
  });

  return (
    <div className={PC_CLASSES} style={style}>
      <PageHeader
        overline="Players"
        title="Compare players"
        subtitle={`Up to three players, same scope (${scope.toLowerCase()}), section by section. The leader in each row is bold in their team colour.`}
        actions={<ScopeSelect value={filter} onChange={(f) => go(ids, f)} />}
      />

      <FaceOff
        slots={ids.map((id, i) => ({ id, profile: failed[i] ? undefined : profiles[i], failed: failed[i] }))}
        names={slotNames.filter((_, i) => live.some((x) => x.i === i))}
        total={total}
        onRemove={(id) => go(ids.filter((x) => x !== id))}
        onAdd={(id) => go([...ids, id])}
      />

      {ids.length === 0 ? (
        <EmptyState
          icon={Columns3}
          title="Pick two or three players"
          why="Search above to add players. Each gets the same overview, batting, bowling, fielding and fantasy rows, plus a skill radar and season trends."
          action={{ href: compareHref(["ba607b88", "740742ef"], {}), label: "Try Virat Kohli vs Rohit Sharma" }}
        />
      ) : hardError ? (
        <QueryError error={hardError.error} onRetry={() => profileQs.forEach((q) => q.isError && q.refetch())} what="the comparison" />
      ) : pending ? (
        <div role="status" aria-busy="true" aria-label="Loading comparison" className="grid grid-cols-1 gap-4 lg:gap-6 xl:grid-cols-2">
          {Array.from({ length: 4 }, (_, i) => (
            <Skeleton key={i} className="h-80 rounded-xl" />
          ))}
        </div>
      ) : subjects.length === 0 ? (
        <p className="text-sm text-muted-foreground">None of these ids is an IPL player. Remove them and search above.</p>
      ) : (
        <div className={cn("transition-opacity", stale && "opacity-60")} aria-busy={profileQs.some((q) => q.isFetching)}>
          {subjects.length === 1 && <p className="mb-3 text-sm text-muted-foreground">Add at least one more player to see who leads each row.</p>}

          {/* Two stacks on xl (balanced heights); on smaller screens the stacks dissolve and `order` restores the reading order. */}
          <div className="grid grid-cols-1 gap-4 lg:gap-6 xl:grid-cols-2 xl:items-start">
            <div className="contents xl:grid xl:content-start xl:gap-6">
              <MetricCard id="overview" title="Overview" icon={<LayoutDashboard />} accent={ACCENT.overview} rows={sections.overview} players={subjects} names={names} className="order-1 xl:order-none" />
              <MetricCard
                id="batting"
                title="Batting"
                icon={<BatIcon />}
                accent={ACCENT.batting}
                rows={sections.batting}
                players={subjects}
                names={names}
                empty="Nobody batted in this scope."
                footnote="Rates compete only with enough sample: ≥ 30 balls for strike rate and dot %, ≥ 5 innings for average. * = below that."
                className="order-2 xl:order-none"
              />
              <MetricCard id="fielding" title="Fielding" icon={<GlovesIcon />} accent={ACCENT.fielding} rows={sections.fielding} players={subjects} names={names} className="order-4 xl:order-none" />
            </div>
            <div className="contents xl:grid xl:content-start xl:gap-6">
              <MetricCard
                id="bowling"
                title="Bowling"
                icon={<BallIcon />}
                accent={ACCENT.bowling}
                rows={sections.bowling}
                players={subjects}
                names={names}
                empty="Nobody bowled in this scope."
                footnote="Economy and dot % compete from 30 balls, average and strike rate from 3 wickets. * = below that."
                className="order-3 xl:order-none"
              />
              <MetricCard
                id="fantasy"
                title="Fantasy"
                icon={<Sparkles />}
                accent={ACCENT.fantasy}
                rows={sections.fantasy}
                players={subjects}
                names={names}
                empty={fantasyQs.some((q) => q.isPending) ? "Loading fantasy points…" : "No Dream11 points in this scope."}
                footnote="Dream11 points per match from scored IPL matches; rates compete from 5 matches."
                className="order-5 xl:order-none"
              />
            </div>
          </div>

          <h2 className="text-overline mt-8 mb-3 text-muted-foreground">Deeper comparison</h2>
          <div className="grid grid-cols-1 gap-4 lg:gap-6 xl:grid-cols-2 xl:items-start">
            <SkillRadar ids={subjects.map((s) => s.id)} names={names} filter={filter} />
            <SeasonChart profiles={live.map((x) => x.p)} fantasies={live.map((x) => fantasyQs[x.i].data)} names={names} />
            <FantasyCompare queries={live.map((x) => fantasyQs[x.i])} names={names} scopeLabel={scope} />
            <MetricCard
              id="splits"
              title="Phase & matchup splits"
              icon={<Swords />}
              accent={ACCENT.matchups}
              rows={sections.splits}
              players={subjects}
              names={names}
              empty="No phase or matchup data in this scope."
              footnote="Phases: powerplay overs 1–6, middle 7–15, death 16–20. Pace / spin and batting hand from player attributes; splits compete from 30 balls (average from 3 dismissals)."
            />
          </div>
        </div>
      )}
    </div>
  );
}
