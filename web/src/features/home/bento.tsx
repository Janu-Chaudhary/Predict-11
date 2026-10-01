import { ArrowLeftRight, ChevronRight, ListOrdered, MapPin, Trophy, Users, type LucideIcon } from "lucide-react";
import Link from "next/link";
import type { ReactNode } from "react";

import { TeamBadge } from "@/components/player/team-badge";
import { cn } from "@/lib/utils";

import type { HomeTiles } from "./types";

function Tile({
  href,
  icon: Icon,
  label,
  children,
  className,
}: {
  href: string;
  icon: LucideIcon;
  label: string;
  children: ReactNode;
  className?: string;
}) {
  return (
    <Link
      href={href}
      className={cn(
        "group flex min-h-[132px] flex-col gap-2 rounded-xl border border-border bg-card p-3 transition-colors hover:bg-surface-2 md:p-4",
        className,
      )}
    >
      <span className="flex items-center gap-2 text-overline text-muted-foreground">
        <Icon className="size-4" strokeWidth={1.75} aria-hidden />
        {label}
        <ChevronRight className="ml-auto size-4 transition-transform group-hover:translate-x-0.5" aria-hidden />
      </span>
      {children}
    </Link>
  );
}

const Big = ({ children }: { children: ReactNode }) => (
  <span className="font-display text-[28px] leading-8 font-bold [font-stretch:75%] num">{children}</span>
);
const Meta = ({ children }: { children: ReactNode }) => <span className="text-xs text-muted-foreground">{children}</span>;
const Empty = () => <Meta>Stats unavailable right now.</Meta>;

/** Overview bento (§2.5: Home only) linking to the explore areas, each with a live mini-stat. */
export function Bento({ tiles }: { tiles: HomeTiles | null }) {
  const t = tiles;
  return (
    <section aria-labelledby="explore-title" className="mt-8 lg:mt-10">
      <h2 id="explore-title" className="mb-3 text-overline text-muted-foreground">
        Explore
      </h2>
      <div className="grid grid-cols-2 gap-3 md:gap-4 lg:grid-cols-4">
        <Tile href="/table" icon={ListOrdered} label="Points table" className="col-span-2 lg:row-span-2">
          {t?.table ? (
            <>
              <span className="flex items-center gap-3">
                <TeamBadge team={t.table.leader.short_code} size="lg" />
                <span>
                  <Big>{t.table.leader.short_code}</Big>
                  <span className="block text-sm text-muted-foreground">
                    top of the {t.table.season} league · <span className="num">{t.table.leader_points}</span> pts from{" "}
                    <span className="num">{t.table.played}</span>
                  </span>
                </span>
              </span>
              {t.table.champion && (
                <span className="mt-auto flex items-center gap-2 text-sm">
                  <TeamBadge team={t.table.champion.short_code} size="sm" />
                  <span>
                    <span className="text-gold-text font-semibold">Champions</span> {t.table.champion.name}
                  </span>
                </span>
              )}
            </>
          ) : (
            <Empty />
          )}
        </Tile>
        <Tile href="/h2h" icon={ArrowLeftRight} label="Head-to-head">
          {t?.h2h ? (
            <>
              <Big>
                {t.h2h.team_a.short_code} v {t.h2h.team_b.short_code}
              </Big>
              <Meta>
                Most-played rivalry · <span className="num">{t.h2h.matches}</span> games,{" "}
                <span className="num">
                  {t.h2h.a_wins}–{t.h2h.b_wins}
                </span>
              </Meta>
            </>
          ) : (
            <Empty />
          )}
        </Tile>
        <Tile href="/players" icon={Users} label="Players">
          {t?.players?.top_runs ? (
            <>
              <Big>{t.players.top_runs.value}</Big>
              <Meta>
                Most runs {t.players.season}: {t.players.top_runs.name}
                {t.players.top_runs.team ? ` (${t.players.top_runs.team})` : ""}
                {t.players.top_wickets ? ` · ${t.players.top_wickets.value} wkts ${t.players.top_wickets.name}` : ""}
              </Meta>
            </>
          ) : (
            <Empty />
          )}
        </Tile>
        <Tile href="/venues" icon={MapPin} label="Venues">
          {t?.venues ? (
            <>
              <Big>{t.venues.top_par ?? t.venues.venues_used}</Big>
              <Meta>
                {t.venues.top_par_venue
                  ? `Highest par ${t.venues.season}: ${t.venues.top_par_venue.name}${t.venues.top_par_venue.city ? `, ${t.venues.top_par_venue.city}` : ""}`
                  : `${t.venues.venues_used} venues in ${t.venues.season}`}
              </Meta>
            </>
          ) : (
            <Empty />
          )}
        </Tile>
        <Tile href="/records" icon={Trophy} label="Records">
          {t?.records ? (
            <>
              <Big>
                {t.records.runs}/{t.records.wickets}
              </Big>
              <Meta>
                Highest total: {t.records.team.short_code} v {t.records.opponent.short_code}, {t.records.year}
              </Meta>
            </>
          ) : (
            <Empty />
          )}
        </Tile>
      </div>
    </section>
  );
}
