"use client";

import { Trophy } from "lucide-react";
import Link from "next/link";

import { GridPageSkeleton } from "@/components/loaders/page-skeletons";
import { TeamBadge } from "@/components/player/team-badge";
import { PageHeader, SectionHeader } from "@/components/shell/page-header";
import { CURRENT_SEASON } from "@/lib/seasons";
import { getTeam } from "@/lib/tokens";

import { ordinal } from "../format";
import { usePointsTable, useTeams } from "../queries";
import type { TeamSummary } from "../types";
import { ErrorState } from "./states";

export function seasonSpan(seasons: number[]): string {
  if (!seasons.length) return "–";
  const first = seasons[0];
  const last = seasons[seasons.length - 1];
  return first === last ? String(first) : `${first}–${last}`;
}

function Kpi({ label, value, sub }: { label: string; value: string; sub?: string }) {
  return (
    <div className="min-w-0 rounded-lg bg-surface-2/70 px-3 py-2">
      <dt className="text-overline text-muted-foreground">{label}</dt>
      <dd className="font-display num text-2xl leading-8 font-bold [font-stretch:80%]">{value}</dd>
      {sub && <dd className="num truncate text-[11px] text-muted-foreground">{sub}</dd>}
    </div>
  );
}

/** Current franchise: large crest, name, and KPI boxes (titles, seasons, latest finish). */
function TeamCard({ t, finish }: { t: TeamSummary; finish?: { year: number; position: number; teams: number } }) {
  const theme = getTeam(t.short_code);
  return (
    <li>
      <Link
        href={`/teams/${encodeURIComponent(t.short_code)}`}
        className="group relative flex h-full flex-col gap-4 overflow-hidden rounded-2xl border border-border bg-card p-5 shadow-e1 outline-none transition-colors hover:bg-surface-2/60 focus-visible:ring-2 focus-visible:ring-ring"
      >
        {/* Team colour as accent: top bar plus a faint wash behind the crest. */}
        <span aria-hidden className="absolute inset-x-0 top-0 h-1" style={{ backgroundColor: theme.primary }} />
        <span aria-hidden className="pointer-events-none absolute -top-16 -right-16 size-56 rounded-full opacity-[0.08] blur-2xl" style={{ backgroundColor: theme.primary }} />
        <div className="flex items-center gap-4">
          <TeamBadge team={t.short_code} size="2xl" className="transition-transform duration-200 group-hover:scale-105 motion-reduce:transition-none" />
          <div className="min-w-0 flex-1">
            <p className="text-overline text-muted-foreground">{t.short_code}</p>
            <h3 className="font-display text-2xl leading-7 font-bold [font-stretch:85%]">{t.name}</h3>
            {t.former_names.length > 0 && (
              <p className="mt-1 truncate text-xs text-faint">
                Formerly {t.former_names.filter((e) => e.name !== t.name).map((e) => e.name).join(", ") || t.former_names[0].name}
              </p>
            )}
          </div>
        </div>
        <dl className="grid grid-cols-3 gap-2">
          <Kpi label="Titles" value={String(t.titles.length)} sub={t.titles.length ? t.titles.join(", ") : "–"} />
          <Kpi label="Seasons" value={String(t.seasons.length)} sub={seasonSpan(t.seasons)} />
          <Kpi label={finish ? `${finish.year} finish` : "Last finish"} value={finish ? ordinal(finish.position) : "–"} sub={finish ? `of ${finish.teams}` : undefined} />
        </dl>
        {t.titles.length > 0 && (
          <p className="flex items-center gap-1" aria-label={`${t.titles.length} titles`}>
            {t.titles.map((y) => (
              <Trophy key={y} aria-hidden className="size-4 text-gold-text" />
            ))}
          </p>
        )}
      </Link>
    </li>
  );
}

/** Former franchise: compact row card (monogram, span). */
function FormerCard({ t }: { t: TeamSummary }) {
  return (
    <li>
      <Link
        href={`/teams/${encodeURIComponent(t.short_code)}`}
        className="flex items-center gap-3 rounded-xl border border-border bg-card px-4 py-3 outline-none transition-colors hover:bg-surface-2 focus-visible:ring-2 focus-visible:ring-ring"
      >
        <TeamBadge team={t.short_code} size="lg" />
        <div className="min-w-0">
          <h3 className="truncate text-sm font-semibold">{t.name}</h3>
          <p className="num text-xs text-muted-foreground">
            {seasonSpan(t.seasons)} · {t.seasons.length} season{t.seasons.length === 1 ? "" : "s"}
          </p>
        </div>
      </Link>
    </li>
  );
}

export function TeamsGrid() {
  const q = useTeams();
  const latest = q.data ? Math.max(...q.data.flatMap((t) => t.seasons)) : CURRENT_SEASON;
  const table = usePointsTable(latest);
  if (q.isPending) return <GridPageSkeleton label="Loading teams" count={10} />;
  const header = <PageHeader overline="IPL" title="Teams" subtitle="Every franchise since 2008. Tap through for season-by-season finishes, results and head-to-heads." />;
  if (q.isError)
    return (
      <>
        {header}
        <ErrorState title="Couldn't load teams" error={q.error} onRetry={() => q.refetch()} />
      </>
    );
  const active = q.data.filter((t) => t.active).sort((a, b) => b.titles.length - a.titles.length || a.name.localeCompare(b.name));
  const defunct = q.data.filter((t) => !t.active).sort((a, b) => a.seasons[0] - b.seasons[0]);
  return (
    <>
      {header}
      <section aria-labelledby="active-h">
        <SectionHeader id="active-h" title={`Current franchises · ${active.length}`} />
        <ul className="grid grid-cols-1 gap-4 md:grid-cols-2 2xl:grid-cols-3">
          {active.map((t) => {
            const row = table.data?.rows.find((r) => r.team.id === t.id);
            return <TeamCard key={t.id} t={t} finish={row ? { year: latest, position: row.position, teams: table.data!.rows.length } : undefined} />;
          })}
        </ul>
      </section>
      {defunct.length > 0 && (
        <section aria-labelledby="defunct-h" className="mt-8">
          <SectionHeader id="defunct-h" title={`Former franchises · ${defunct.length}`} />
          <ul className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
            {defunct.map((t) => (
              <FormerCard key={t.id} t={t} />
            ))}
          </ul>
        </section>
      )}
    </>
  );
}
