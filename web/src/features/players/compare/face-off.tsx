"use client";

import { Plus, X } from "lucide-react";
import Link from "next/link";
import { Fragment } from "react";

import { PlayerAvatar } from "@/components/player/player-avatar";
import { TeamBadge } from "@/components/player/team-badge";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";

import { MAX_COMPARE } from "../constants";
import { displayName, fmt, photoOf, seasonSpan, teamCode } from "../format";
import { PlayerPicker } from "../player-picker";
import type { PlayerProfile } from "../types";
import { pcVar } from "./colours";
import type { Tally } from "./metrics";

type Slot = { id: string; profile?: PlayerProfile; failed?: boolean };

/**
 * Face-off band: frameless cut-outs straight on the page background with name, crest, matches and
 * seasons, "vs" between players, and the add-player picker in the free slot. Ends with the overall
 * tally strip (rows won per player across every section).
 */
export function FaceOff({
  slots,
  names,
  total,
  onRemove,
  onAdd,
}: {
  slots: Slot[];
  names: string[];
  total: Tally | null;
  onRemove: (id: string) => void;
  onAdd: (id: string) => void;
}) {
  const canAdd = slots.length < MAX_COMPARE;
  return (
    <section aria-label="Players compared" className="mb-6">
      <div className={cn("flex flex-wrap items-stretch justify-center gap-y-4 lg:flex-nowrap", slots.length === 0 && "justify-start")}>
        {slots.map((s, i) => (
          <Fragment key={s.id}>
            {i > 0 && (
              <div aria-hidden className={cn("flex shrink-0 items-center justify-center self-center pb-16 sm:w-14 md:pb-20", slots.length === 3 ? "w-5" : "w-8")}>
                <span className="font-display text-lg font-bold text-faint italic sm:text-2xl">vs</span>
              </div>
            )}
            <PlayerColumn slot={s} index={i} onRemove={() => onRemove(s.id)} count={slots.length} />
          </Fragment>
        ))}
        {canAdd && (
          <div className={cn("flex w-full flex-col justify-center lg:w-auto lg:min-w-72 lg:flex-1", slots.length > 0 && "lg:ml-6 lg:max-w-sm")}>
            <div className="flex flex-col gap-2 rounded-xl border border-dashed border-border bg-card/40 p-4 lg:min-h-48 lg:justify-center">
              <p className="text-overline flex items-center gap-1.5 text-muted-foreground">
                <Plus aria-hidden className="size-3.5" />
                {slots.length === 0 ? "Pick the first player" : slots.length === 1 ? "Add a player to compare" : "Add a third player"}
              </p>
              <PlayerPicker
                label={slots.length === 0 ? "First player" : "Add a player"}
                hideLabel
                placeholder={slots.length === 0 ? "Search the first player…" : "Search a player…"}
                value={null}
                exclude={slots.map((s) => s.id)}
                onChange={(p) => p && onAdd(p.id)}
              />
            </div>
          </div>
        )}
      </div>
      {total && total.contested > 0 && slots.length >= 2 && <TotalStrip total={total} names={names} />}
    </section>
  );
}

function PlayerColumn({ slot, index, count, onRemove }: { slot: Slot; index: number; count: number; onRemove: () => void }) {
  const p = slot.profile;
  const name = p ? displayName(p) : slot.id;
  const code = teamCode(p?.last_team) ?? undefined;
  return (
    <div className={cn("relative flex min-w-0 flex-col items-center text-center", count === 3 ? "w-[calc((100%-2.5rem)/3)] sm:w-[calc((100%-7rem)/3)] lg:w-auto lg:flex-1" : "w-[calc((100%-2rem)/2)] sm:w-[calc((100%-3.5rem)/2)] lg:w-auto lg:flex-1", count === 1 && "w-full lg:max-w-md")}>
      <div className="relative flex items-end justify-center">
        <button
          type="button"
          onClick={onRemove}
          aria-label={`Remove ${name} from comparison`}
          className="absolute top-0 -right-6 z-10 inline-flex size-9 items-center justify-center rounded-lg text-muted-foreground outline-none hover:bg-surface-2 hover:text-foreground focus-visible:ring-2 focus-visible:ring-ring max-md:-right-3 max-md:size-8"
        >
          <X aria-hidden className="size-4" />
        </button>
        {/* soft team-colour glow behind the cut-out */}
        <span aria-hidden className="absolute inset-x-[-15%] bottom-0 h-3/4 rounded-full opacity-25 blur-2xl" style={{ background: pcVar(index) }} />
        {p ? (
          <PlayerAvatar name={name} src={photoOf(p)} team={code} size="hero" eager className="relative max-md:size-[104px]!" />
        ) : slot.failed ? (
          <span className="relative flex size-[176px] items-center justify-center text-sm text-muted-foreground max-md:size-[104px]">Unknown id</span>
        ) : (
          <Skeleton className="relative size-[176px] rounded-2xl max-md:size-[104px]" />
        )}
      </div>
      <span aria-hidden className="h-1 w-3/5 max-w-40 rounded-full" style={{ background: pcVar(index) }} />
      <div className="mt-2 w-full min-w-0">
        {p ? (
          <>
            <Link
              href={`/players/${encodeURIComponent(p.id)}`}
              className="font-display block truncate rounded text-base leading-6 font-bold outline-none hover:underline focus-visible:ring-2 focus-visible:ring-ring sm:text-xl md:text-2xl md:leading-8"
            >
              {name}
            </Link>
            <p className="mt-0.5 flex min-w-0 items-center justify-center gap-1.5 text-xs text-muted-foreground sm:text-sm">
              {code && <TeamBadge team={code} showCode={false} />}
              <span className="truncate">{p.last_team ?? "IPL player"}</span>
            </p>
            <p className="num mt-1 text-xs text-muted-foreground sm:text-sm">
              <span className="font-semibold text-foreground">{fmt(p.matches)}</span> matches
              <span className="max-sm:hidden">
                {" · "}
                {seasonSpan(p.seasons)}
              </span>
            </p>
          </>
        ) : slot.failed ? (
          <p className="text-sm text-muted-foreground">No IPL player “{slot.id}”</p>
        ) : (
          <div className="flex flex-col items-center gap-1.5">
            <Skeleton className="h-6 w-36" />
            <Skeleton className="h-4 w-28" />
          </div>
        )}
      </div>
    </div>
  );
}

/** Overall rows won, as a proportional strip in player colours plus printed counts. */
function TotalStrip({ total, names }: { total: Tally; names: string[] }) {
  const won = total.wins.reduce((a, b) => a + b, 0);
  return (
    <div className="mx-auto mt-5 max-w-3xl">
      <div className="mb-1.5 flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1">
        <span className="text-overline text-muted-foreground">Rows won · {total.contested} contested</span>
        <span className="num flex flex-wrap gap-x-3 text-sm">
          {names.map((n, i) => (
            <span key={n} className="inline-flex items-center gap-1.5">
              <span aria-hidden className="size-2 rounded-full" style={{ background: pcVar(i) }} />
              {n} <b className="font-bold" style={{ color: pcVar(i) }}>{total.wins[i]}</b>
            </span>
          ))}
        </span>
      </div>
      <div aria-hidden className="flex h-2 gap-0.5 overflow-hidden rounded-full bg-surface-2">
        {won > 0 && total.wins.map((w, i) => <span key={i} className="h-full" style={{ width: `${(w / won) * 100}%`, background: pcVar(i) }} />)}
      </div>
    </div>
  );
}
