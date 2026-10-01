"use client";

import { ArrowRight } from "lucide-react";
import Link from "next/link";
import { useEffect, useState, useSyncExternalStore } from "react";

import { TeamBadge } from "@/components/player/team-badge";
import { useResolvedTheme } from "@/hooks/use-resolved-theme";
import { teamChartColour } from "@/lib/tokens";
import { cn } from "@/lib/utils";

import styles from "./home.module.css";
import { countdown, pad2 } from "./lib/countdown";
import type { HomeMatch, HomeState, HomeTeam, NextFixture, SeasonCard } from "./types";

const CTA = "inline-flex h-11 flex-1 items-center justify-center gap-1.5 rounded-[10px] px-3 text-sm font-semibold";
const CTA_GOLD = cn(CTA, "bg-primary text-primary-foreground hover:bg-primary/90");
const CTA_OUTLINE = cn(CTA, "border border-border text-foreground hover:bg-surface-2");

function Overline({ id, children }: { id?: string; children: React.ReactNode }) {
  return (
    <div id={id} className="text-overline text-muted-foreground">
      {children}
    </div>
  );
}

/** Two teams with badges and a 2 px team-colour underline under each name (§2.3). */
function Teams({ a, b }: { a: HomeTeam; b: HomeTeam }) {
  const theme = useResolvedTheme();
  const side = (t: HomeTeam, right: boolean) => (
    <div className={cn("flex flex-col gap-2", right ? "items-end text-right" : "items-start")}>
      <TeamBadge team={t.short_code} size="xl" opponent={right ? a.short_code : undefined} side={right ? "away" : "home"} />
      <div className="font-display text-[28px] leading-none font-[650] [font-stretch:87.5%]">
        {t.short_code}
        <span
          aria-hidden
          className={cn("mt-1.5 block h-0.5 w-8 rounded-full", right && "ml-auto")}
          style={{ background: teamChartColour(t.short_code, theme) }}
        />
      </div>
      <span className="sr-only">{t.name}</span>
    </div>
  );
  return (
    <div className="my-4 grid grid-cols-[1fr_auto_1fr] items-center gap-3">
      {side(a, false)}
      <div className="font-display text-sm text-faint">vs</div>
      {side(b, true)}
    </div>
  );
}

const noop = () => () => {};
function useMounted() {
  return useSyncExternalStore(noop, () => true, () => false);
}

function Digit({ value, unit }: { value: string; unit: string }) {
  return (
    <div className="flex-1 overflow-hidden rounded-[10px] bg-surface-2 py-2 text-center">
      <b key={value} className={cn("block font-display text-4xl leading-10 font-bold [font-stretch:75%] num", styles.flip)}>
        {value}
      </b>
      <span className="text-overline text-muted-foreground">{unit}</span>
    </div>
  );
}

/** Countdown to the start; flips each changed digit (320 ms), static under reduced motion. */
export function Countdown({ start }: { start: string }) {
  const mounted = useMounted();
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    const t = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(t);
  }, []);
  const c = countdown(Date.parse(start), now);
  const cells: [string, string][] =
    c.days > 0
      ? [
          [pad2(c.days), "days"],
          [pad2(c.hours), "hrs"],
          [pad2(c.minutes), "min"],
        ]
      : [
          [pad2(c.hours), "hrs"],
          [pad2(c.minutes), "min"],
          [pad2(c.seconds), "sec"],
        ];
  return (
    <div className="mt-2 mb-4 flex gap-2" role="timer" aria-live="off" aria-label="Time to start">
      {cells.map(([v, u]) => (
        <Digit key={u} value={mounted ? v : "--"} unit={u} />
      ))}
    </div>
  );
}

function FixtureCard({ f }: { f: NextFixture }) {
  const when = new Date(f.start).toLocaleString("en-IN", {
    weekday: "short",
    day: "numeric",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
    timeZone: "Asia/Kolkata",
  });
  return (
    <>
      <Overline id="home-card-title">
        Next match · {f.title}
        {f.venue ? ` · ${f.venue.name}${f.venue.city ? `, ${f.venue.city}` : ""}` : ""}
      </Overline>
      <Teams a={f.team1} b={f.team2} />
      <Countdown start={f.start} />
      <div className="mb-4 flex flex-wrap gap-2">
        <span
          className={cn(
            "rounded-full border px-2.5 py-1 text-xs",
            f.status === "xi_confirmed" ? "border-info/40 text-info" : "border-warning/40 text-warning",
          )}
        >
          {f.status === "xi_confirmed" ? "XI confirmed" : "Provisional · XI at toss"}
        </span>
        <span className="rounded-full border border-border px-2.5 py-1 text-xs text-muted-foreground">{when} IST</span>
      </div>
      <div className="flex gap-2">
        <Link href="/build" className={CTA_GOLD}>
          Build my XI <ArrowRight className="size-4" aria-hidden />
        </Link>
        <Link href={f.id ? `/matches/${f.id}` : "/matches"} className={CTA_OUTLINE}>
          Match centre
        </Link>
      </div>
    </>
  );
}

function ScoreLines({ m }: { m: HomeMatch }) {
  const teams = { [m.team1.id]: m.team1, [m.team2.id]: m.team2 };
  return (
    <ul className="grid gap-1.5">
      {m.scores.map((s) => {
        const t = teams[s.team_id];
        const won = s.team_id === m.winner_id;
        return (
          <li key={s.innings} className="flex items-baseline justify-between gap-3">
            <span className={cn("flex items-center gap-2", won ? "font-semibold" : "text-muted-foreground")}>
              <TeamBadge team={t?.short_code ?? "?"} size="sm" />
              {t?.name}
            </span>
            <span className="shrink-0 font-display text-xl font-bold whitespace-nowrap [font-stretch:75%] num">
              {s.runs}/{s.wickets}
              <span className="ml-1.5 font-sans text-xs font-normal text-muted-foreground">({s.overs} ov)</span>
            </span>
          </li>
        );
      })}
    </ul>
  );
}

function OffSeasonCard({ season, last }: { season: SeasonCard; last: HomeMatch | null }) {
  const champ = season.champion;
  return (
    <>
      <Overline id="home-card-title">Off-season · IPL {season.year} complete</Overline>
      <p className="mt-3 font-display text-[28px] leading-8 font-[650] [font-stretch:87.5%] lg:text-[32px] lg:leading-9">
        {season.next_season}
      </p>
      <p className="mt-1 text-sm text-muted-foreground">
        Fixtures, squads and projections switch on when the schedule is announced.
      </p>
      {champ && (
        <div className="mt-5 flex items-center gap-3 rounded-[10px] bg-surface-2 p-3">
          <TeamBadge team={champ.short_code} size="lg" />
          <div className="min-w-0">
            <div className="text-overline text-gold-text">Champions {season.year}</div>
            <div className="truncate font-semibold">{champ.name}</div>
          </div>
        </div>
      )}
      {last && (
        <div className="mt-4">
          <div className="mb-2 text-xs text-muted-foreground">
            {last.title}
            {last.venue ? ` · ${last.venue.name}` : ""} ·{" "}
            {new Date(last.date).toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric" })}
          </div>
          <ScoreLines m={last} />
          <p className="mt-2 text-sm font-medium">{last.result}</p>
        </div>
      )}
      <div className="mt-5 flex gap-2">
        <Link href={`/table?season=${season.year}`} className={CTA_GOLD}>
          {season.year} table <ArrowRight className="size-4" aria-hidden />
        </Link>
        <Link href="/records" className={CTA_OUTLINE}>
          Records
        </Link>
      </div>
    </>
  );
}

function LastMatchCard({ m }: { m: HomeMatch }) {
  return (
    <>
      <Overline id="home-card-title">
        Last match · {m.title}
        {m.venue ? ` · ${m.venue.name}` : ""}
      </Overline>
      <Teams a={m.team1} b={m.team2} />
      <ScoreLines m={m} />
      <p className="mt-2 mb-5 text-sm font-medium">{m.result}</p>
      <div className="flex gap-2">
        <Link href={`/matches/${m.id}`} className={CTA_GOLD}>
          Match centre <ArrowRight className="size-4" aria-hidden />
        </Link>
        <Link href="/table" className={CTA_OUTLINE}>
          Table
        </Link>
      </div>
    </>
  );
}

/** The card shared by every hero concept (§7): next fixture, else last result / off-season. */
export function MatchCard({ state }: { state: HomeState }) {
  let body: React.ReactNode = null;
  if (state.next_fixture) body = <FixtureCard f={state.next_fixture} />;
  else if (state.phase === "off_season" && state.season) body = <OffSeasonCard season={state.season} last={state.last_match} />;
  else if (state.last_match) body = <LastMatchCard m={state.last_match} />;
  if (!body) return null;
  return (
    <section aria-labelledby="home-card-title" className="relative rounded-2xl border border-border bg-card p-5 shadow-e1">
      {body}
    </section>
  );
}
