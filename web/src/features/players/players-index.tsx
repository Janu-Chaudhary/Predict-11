"use client";

import { ArrowLeftRight, Columns3, History, Trophy } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";

import { PlayerRow } from "@/components/data/player-row";
import { PlayerAvatar } from "@/components/player/player-avatar";
import { TeamBadge } from "@/components/player/team-badge";

import { teamCode } from "./format";
import { PlayerPicker } from "./player-picker";
import { useRecentPlayers } from "./recent";
import { SeasonLeaders } from "./season-leaders";
import { Panel } from "./ui";

/**
 * Well-known current players (Cricsheet registry ids) for a useful first screen before any search.
 * Static on purpose: a "popular" endpoint doesn't exist yet. Teams are their last IPL side.
 */
export const POPULAR_PLAYERS = [
  { id: "ba607b88", name: "Virat Kohli", team: "Royal Challengers Bengaluru", note: "Most IPL runs" },
  { id: "462411b3", name: "Jasprit Bumrah", team: "Mumbai Indians", note: "Death-overs specialist" },
  { id: "740742ef", name: "Rohit Sharma", team: "Mumbai Indians", note: "Opener" },
  { id: "4a8a2e3b", name: "MS Dhoni", team: "Chennai Super Kings", note: "Finisher, WK" },
  { id: "271f83cd", name: "Suryakumar Yadav", team: "Mumbai Indians", note: "360° batter" },
  { id: "5f547c8b", name: "Rashid Khan", team: "Gujarat Titans", note: "Leg-spin" },
  { id: "fe93fd9d", name: "Ravindra Jadeja", team: "Rajasthan Royals", note: "All-rounder" },
  { id: "9d430b40", name: "Sunil Narine", team: "Kolkata Knight Riders", note: "All-rounder" },
  { id: "b4b99816", name: "Shubman Gill", team: "Gujarat Titans", note: "Opener" },
  { id: "99b75528", name: "Jos Buttler", team: "Gujarat Titans", note: "Opener, WK" },
  { id: "57ee1fde", name: "Yuzvendra Chahal", team: "Punjab Kings", note: "Most IPL wickets" },
  { id: "12b610c2", name: "Travis Head", team: "Sunrisers Hyderabad", note: "Powerplay hitter" },
];

/** Season the index rail ranks (latest completed IPL). */
const CURRENT_SEASON = 2026;

export function PlayersIndex() {
  const router = useRouter();
  const recent = useRecentPlayers();

  return (
    <div className="grid grid-cols-1 gap-4 lg:grid-cols-12 lg:gap-6">
      <div className="grid grid-cols-1 content-start gap-4 lg:col-span-8">
        <Panel>
          <PlayerPicker
            label="Find a player"
            placeholder="Name or alias, e.g. Virat, Bumrah, Dhoni"
            value={null}
            onChange={(p) => p && router.push(`/players/${encodeURIComponent(p.id)}`)}
          />
          <p className="mt-2 text-xs text-muted-foreground">Matches full names, scorecard names and known aliases (“Virat”, “V Kohli”). Only players with IPL matches are listed.</p>
        </Panel>

        {recent.length > 0 && (
          <Panel title={<span className="inline-flex items-center gap-1.5"><History aria-hidden className="size-3.5" /> Recently viewed</span>} bodyClassName="px-0 pb-1 md:px-0">
            <ul className="divide-y divide-border">
              {recent.map((p) => (
                <li key={p.id}>
                  <PlayerRow player={{ id: p.id, name: p.name, team: teamCode(p.team) ?? "", photoUrl: p.image }} meta={p.team ?? undefined} />
                </li>
              ))}
            </ul>
          </Panel>
        )}

        <Panel title="Popular players" id="popular">
          <ul className="grid grid-cols-1 gap-2 sm:grid-cols-2 md:gap-3 2xl:grid-cols-3">
            {POPULAR_PLAYERS.map((p) => {
              const code = teamCode(p.team) ?? "";
              return (
                <li key={p.id}>
                  <Link
                    href={`/players/${encodeURIComponent(p.id)}`}
                    className="flex h-full items-end gap-3 overflow-hidden rounded-xl border border-border bg-surface-2/40 pr-3 outline-none hover:bg-surface-2 focus-visible:ring-2 focus-visible:ring-ring"
                  >
                    <PlayerAvatar name={p.name} src={`/players/${p.id}-256.webp`} team={code} size="xl" className="mt-2 shrink-0" />
                    <span className="min-w-0 flex-1 self-center py-3">
                      <span className="font-display block truncate text-lg leading-6 font-bold">{p.name}</span>
                      <span className="block truncate text-sm text-muted-foreground">{p.note}</span>
                      <span className="mt-1 flex items-center gap-1.5 text-xs text-muted-foreground">
                        <TeamBadge team={code} />
                      </span>
                    </span>
                  </Link>
                </li>
              );
            })}
          </ul>
        </Panel>

        <nav aria-label="Player tools" className="grid grid-cols-1 gap-4 xl:grid-cols-3">
          <ToolCard
            href="/fantasy"
            icon={Trophy}
            title="Fantasy leaderboards"
            body="Dream11 points by season: floor, median and ceiling, consistency and points per credit, plus the best XIs."
          />
          <ToolCard
            href="/players/compare?ids=ba607b88,740742ef"
            icon={Columns3}
            title="Compare players"
            body="Two or three players side by side, same filters, best value in each row highlighted."
          />
          <ToolCard
            href="/h2h?batter=ba607b88&bowler=462411b3"
            icon={ArrowLeftRight}
            title="Batter v bowler"
            body="Balls, runs, dismissals and strike rate for any pair, with a sample-size confidence badge."
          />
        </nav>
      </div>

      <aside className="grid grid-cols-1 content-start gap-4 lg:col-span-4" aria-label="Season leaders">
        <SeasonLeaders season={CURRENT_SEASON} />
      </aside>
    </div>
  );
}

function ToolCard({ href, icon: Icon, title, body }: { href: string; icon: typeof Columns3; title: string; body: string }) {
  return (
    <Link
      href={href}
      className="flex gap-3 rounded-xl border border-border bg-card p-4 shadow-e1 outline-none hover:bg-surface-2 focus-visible:ring-2 focus-visible:ring-ring"
    >
      <span className="flex size-10 shrink-0 items-center justify-center rounded-lg bg-surface-2 text-brand">
        <Icon aria-hidden className="size-5" strokeWidth={1.75} />
      </span>
      <span className="min-w-0">
        <span className="block text-sm font-semibold">
          {title} <span aria-hidden>→</span>
        </span>
        <span className="mt-0.5 block text-sm text-muted-foreground">{body}</span>
      </span>
    </Link>
  );
}
