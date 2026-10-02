import { Trophy } from "lucide-react";
import Image from "next/image";
import Link from "next/link";

import { TeamBadge } from "@/components/player/team-badge";
import type { HomeMatch, HomeTeam } from "@/features/home/types";
import { cn } from "@/lib/utils";
import { getJson } from "@/features/venues/api";
import { PhotoCredit } from "@/features/venues/venue-photo";

/** Match header facts from GET /home/match/{id}; null when the id is unknown or the API is down. */
export async function fetchMatchHeader(id: string): Promise<HomeMatch | null> {
  if (!/^\d{1,10}$/.test(id)) return null;
  try {
    return await getJson<HomeMatch>(`/home/match/${id}`, AbortSignal.timeout(4_000));
  } catch {
    return null;
  }
}

/**
 * Ground photo band across the top of the match header card (fades into the card), with the
 * venue name and the photo credit the licence requires. Renders nothing without a photo.
 */
export function MatchVenueBanner({ match }: { match: HomeMatch }) {
  const v = match.venue;
  if (!v?.image_url) return null;
  const when = new Date(match.date).toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric" });
  return (
    <div className="relative -mx-4 -mt-4 mb-1 flex h-40 flex-col justify-end overflow-hidden rounded-t-xl px-4 pb-3 md:h-56">
      <Image src={v.image_url} alt="" fill unoptimized loading="eager" sizes="100vw" className="object-cover" />
      <div aria-hidden className="absolute inset-0 bg-[linear-gradient(to_bottom,transparent_35%,var(--card)_100%)]" />
      <div className="relative z-10 flex flex-wrap items-end justify-between gap-2">
        <div className="w-fit max-w-full rounded-lg bg-black/50 px-3 py-2 text-white backdrop-blur-[3px]">
          <p className="text-overline text-white/80">
            {match.title} · IPL {match.season} · <span className="num">{when}</span>
          </p>
          <Link href={`/venues/${v.id}`} className="font-display text-lg leading-6 font-semibold [font-stretch:87.5%] outline-none hover:underline focus-visible:ring-2 focus-visible:ring-ring md:text-xl">
            {v.name}
            {v.city ? <span className="font-sans text-sm font-normal text-white/80">, {v.city}</span> : null}
          </Link>
        </div>
        {v.image_credit && (
          <div className="max-w-full rounded-full bg-black/45 px-2.5 py-1 text-white/90 backdrop-blur-sm md:max-w-[50%]">
            <PhotoCredit credit={v.image_credit} />
          </div>
        )}
      </div>
    </div>
  );
}

function Side({ team, match, align }: { team: HomeTeam; match: HomeMatch; align: "left" | "right" }) {
  const inns = match.scores.filter((x) => x.team_id === team.id);
  const won = match.winner_id === team.id;
  const lost = match.winner_id !== null && !won;
  return (
    <div className={cn("flex min-w-0 items-center gap-3 md:gap-4", align === "right" && "flex-row-reverse text-right")}>
      <TeamBadge team={team.short_code} size="2xl" className="max-md:scale-75" />
      <div className="min-w-0">
        <Link href={`/teams/${encodeURIComponent(team.short_code)}`} className={cn("block truncate text-sm outline-none hover:underline focus-visible:ring-2 focus-visible:ring-ring md:text-base", won ? "font-semibold" : "text-muted-foreground")}>
          {team.name}
        </Link>
        {inns.length ? (
          inns.map((x) => (
            <p key={x.innings} className={cn("num font-display text-3xl leading-9 font-bold [font-stretch:80%] md:text-4xl md:leading-10", lost && "text-muted-foreground")}>
              {x.runs}/{x.wickets} <span className="font-sans text-xs font-normal text-muted-foreground">({x.overs} ov)</span>
            </p>
          ))
        ) : (
          <p className="text-sm text-faint">Did not bat</p>
        )}
      </div>
    </div>
  );
}

/** Teams, innings scores and the result line for a played match. */
export function MatchScoreHeader({ match, overline = true }: { match: HomeMatch; overline?: boolean }) {
  const when = new Date(match.date).toLocaleDateString("en-IN", { weekday: "short", day: "numeric", month: "short", year: "numeric" });
  const final = (match.stage ?? "").toLowerCase() === "final";
  return (
    <div>
      {overline && (
        <p className="text-overline text-muted-foreground">
          {match.title} · IPL {match.season} · <span className="num">{when}</span>
        </p>
      )}
      <h1 id="match-title" className="sr-only">
        {match.team1.name} v {match.team2.name}, {match.title}, IPL {match.season}
      </h1>
      <div className="mt-3 grid grid-cols-[minmax(0,1fr)_auto_minmax(0,1fr)] items-center gap-3 md:gap-6">
        <Side team={match.team1} match={match} align="left" />
        <span className="text-sm font-medium text-muted-foreground">v</span>
        <Side team={match.team2} match={match} align="right" />
      </div>
      <p className="mt-3 flex items-center justify-center gap-1.5 text-center text-sm font-medium">
        {final && match.winner_id !== null && <Trophy aria-hidden className="size-4 text-gold-text" />}
        {match.result}
        {final && match.winner_id !== null && <span className="text-gold-text">· Champions</span>}
      </p>
    </div>
  );
}
