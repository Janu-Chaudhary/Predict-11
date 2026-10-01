"use client";

import { LayoutGrid, List } from "lucide-react";
import { useState } from "react";

import { PlayerRow } from "@/components/data/player-row";
import { PitchView } from "@/components/pitch/pitch-view";
import type { Player } from "@/lib/mock";
import type { TeamCode } from "@/lib/tokens";

import { displayName, fmt, photoOf } from "../players/format";
import { fmtPts, multiplierLabel, sortXi } from "./format";
import type { XiPick } from "./types";
import { Segmented } from "./ui";

/** XiPick → the builder's Player shape, so the shared PitchView renders it unchanged. */
export function toPitchPlayers(xi: XiPick[]): Player[] {
  return sortXi(xi).map((p) => ({
    id: p.player.id,
    name: displayName(p.player),
    team: (p.team ?? "") as TeamCode,
    role: p.role,
    credits: p.credits ?? 0,
    // Hindsight: the "range" is the realised score, so floor = median = ceiling.
    projection: { floor: p.points, median: p.points, ceiling: p.points },
    captain: p.captain,
    viceCaptain: p.vice_captain,
    photoUrl: photoOf(p.player),
  }));
}

/** List view of an XI: role order, C/VC roundels, raw points and the multiplied score. */
export function XiList({ xi, unit = "pts", showProjected = false, caption }: { xi: XiPick[]; unit?: string; showProjected?: boolean; caption: string }) {
  return (
    <ul aria-label={caption} className="divide-y divide-border">
      {sortXi(xi).map((p) => {
        const mult = multiplierLabel(p);
        return (
          <li key={p.player.id}>
            <PlayerRow
              player={{ id: p.player.id, name: displayName(p.player), team: p.team ?? "", role: p.role, captain: p.captain, viceCaptain: p.vice_captain, photoUrl: photoOf(p.player) }}
              meta={
                <>
                  {showProjected && p.projected !== null && <>form {fmtPts(p.projected)} · </>}
                  {p.matches != null && <>{p.matches} m · {fmtPts(p.mean)} avg · </>}
                  {p.credits !== null && <>{fmt(p.credits, 1)} cr · </>}
                  {fmt(p.points)} {unit}
                  {mult && <> {mult}</>}
                </>
              }
              stat={{ value: fmtPts(p.effective), label: mult ? "with C/VC" : unit }}
            />
          </li>
        );
      })}
    </ul>
  );
}

/** Pitch ⇄ list toggle around one XI (§4.3 "Pitch | List"). */
export function XiPanel({ xi, title, unit = "pts", showProjected = false, footer }: { xi: XiPick[]; title: string; unit?: string; showProjected?: boolean; footer?: React.ReactNode }) {
  const [view, setView] = useState<"pitch" | "list">("pitch");
  return (
    <div className="min-w-0">
      <div className="mb-2 flex justify-end">
        <Segmented<"pitch" | "list">
          label={`${title}: view`}
          value={view}
          onChange={setView}
          options={[
            {
              key: "pitch",
              label: (
                <span className="inline-flex items-center gap-1.5">
                  <LayoutGrid aria-hidden className="size-4" /> Pitch
                </span>
              ),
            },
            {
              key: "list",
              label: (
                <span className="inline-flex items-center gap-1.5">
                  <List aria-hidden className="size-4" /> List
                </span>
              ),
            },
          ]}
        />
      </div>
      {view === "pitch" ? <PitchView players={toPitchPlayers(xi)} /> : <XiList xi={xi} unit={unit} showProjected={showProjected} caption={title} />}
      {footer}
    </div>
  );
}
