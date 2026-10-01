import type { Metadata } from "next";

import { DEFAULT_PAIR } from "@/features/h2h/constants";
import { H2HView } from "@/features/h2h/h2h-view";
import { firstParam, parseSince } from "@/features/players/format";

export const metadata: Metadata = { title: "Head-to-head" };

export default async function H2HPage(props: PageProps<"/h2h">) {
  const sp = await props.searchParams;
  const batter = firstParam(sp.batter)?.trim() || undefined;
  const bowler = firstParam(sp.bowler)?.trim() || undefined;
  const since = parseSince(firstParam(sp.since));
  // Bare /h2h opens on the canonical example (V Kohli v JJ Bumrah); "Clear" both pickers to start fresh.
  const query = !batter && !bowler && !("batter" in sp) && !("bowler" in sp) ? { ...DEFAULT_PAIR, since } : { batter, bowler, since };
  return <H2HView query={query} />;
}
