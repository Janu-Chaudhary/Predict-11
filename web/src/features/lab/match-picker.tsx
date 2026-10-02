"use client";

import { Search } from "lucide-react";
import { useRouter } from "next/navigation";
import { useMemo, useState } from "react";

import { TeamBadge } from "@/components/player/team-badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";

import { PHASE_LABEL, fmtDate, fmtNum } from "./format";
import { useMatches } from "./queries";
import type { MatchRow, Phase } from "./types";
import { Segmented, labHref, useLabState } from "./ui";

export function matchLabel(m: MatchRow["info"]): string {
  return `${m.team1?.code ?? "?"} v ${m.team2?.code ?? "?"}`;
}

export function searchMatches(rows: MatchRow[], q: string): MatchRow[] {
  const needle = q.trim().toLowerCase();
  if (!needle) return rows;
  return rows.filter((r) => {
    const i = r.info;
    const hay = [i.team1?.code, i.team1?.name, i.team2?.code, i.team2?.name, i.venue, i.city, i.date, fmtDate(i.date), i.matchNumber ? `#${i.matchNumber}` : null, String(i.matchId)]
      .filter(Boolean)
      .join(" ")
      .toLowerCase();
    return needle.split(/\s+/).every((w) => hay.includes(w));
  });
}

/** Phase toggle + searchable list of the run's evaluated matches; selection lives in the URL. */
export function MatchPicker({ version, className }: { version: string; className?: string }) {
  const state = useLabState();
  const router = useRouter();
  const [q, setQ] = useState("");
  const matchesQ = useMatches(version, state.phase);
  const rows = useMemo(() => searchMatches(matchesQ.data ?? [], q), [matchesQ.data, q]);
  const go = (patch: Parameters<typeof labHref>[1]) => router.replace(labHref(state, patch), { scroll: false });

  return (
    <section className={cn("flex min-w-0 flex-col rounded-xl border border-border bg-card p-3 shadow-e1", className)} aria-label="Pick a match">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h3 className="text-overline text-muted-foreground">Match</h3>
        <Segmented
          size="sm"
          label="Evaluation set"
          value={state.phase}
          onChange={(p: Phase) => go({ phase: p, match: null, player: null })}
          options={(["test", "walkforward"] as const).map((p) => ({ key: p, label: PHASE_LABEL[p] }))}
        />
      </div>
      <div className="relative mt-2">
        <Search aria-hidden className="pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2 text-muted-foreground" />
        <Input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Team, venue or date" aria-label="Search matches" className="h-9 rounded-[10px] bg-card pl-9" />
      </div>
      <p className="num mt-1.5 text-xs text-muted-foreground">{matchesQ.data ? `${rows.length} of ${matchesQ.data.length} matches` : " "}</p>
      <ul className="mt-1 max-h-64 min-h-24 flex-1 overflow-y-auto overscroll-contain lg:max-h-[34rem]" role="listbox" aria-label="Matches">
        {matchesQ.isPending &&
          Array.from({ length: 6 }, (_, i) => (
            <li key={i} className="py-1">
              <Skeleton className="h-11 rounded-lg" />
            </li>
          ))}
        {matchesQ.isError && <li className="p-2 text-sm text-muted-foreground">Couldn&apos;t load matches: {(matchesQ.error as Error).message}</li>}
        {rows.map((m) => {
          const active = state.match === m.info.matchId;
          return (
            <li key={m.info.matchId} role="option" aria-selected={active}>
              <button
                type="button"
                onClick={() => go({ match: m.info.matchId, player: null })}
                className={cn(
                  "flex w-full items-center gap-2 rounded-lg px-2 py-1.5 text-left outline-none hover:bg-surface-2 focus-visible:ring-2 focus-visible:ring-ring",
                  active && "bg-brand/12 ring-1 ring-brand/40",
                )}
              >
                {m.info.team1 && <TeamBadge team={m.info.team1.code} showCode={false} />}
                <span className="min-w-0 flex-1">
                  <span className="block truncate text-sm font-medium">{matchLabel(m.info)}</span>
                  <span className="num block truncate text-xs text-muted-foreground">
                    {fmtDate(m.info.date)}
                    {m.info.venue ? ` · ${m.info.venue}` : ""}
                  </span>
                </span>
                {m.xiModel !== null && m.xiBase !== null ? (
                  <span className={cn("num shrink-0 text-xs font-medium", m.xiModel > m.xiBase ? "text-positive" : m.xiModel < m.xiBase ? "text-negative" : "text-muted-foreground")} title="Model XI minus baseline XI (actual points)">
                    {m.xiModel - m.xiBase > 0 ? "+" : ""}
                    {fmtNum(m.xiModel - m.xiBase, 0)}
                  </span>
                ) : (
                  <span className="num shrink-0 text-xs text-muted-foreground" title="MAE model">
                    {fmtNum(m.maeModel, 1)}
                  </span>
                )}
              </button>
            </li>
          );
        })}
      </ul>
    </section>
  );
}
