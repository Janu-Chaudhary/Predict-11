import type { Metadata } from "next";

import { CompareView } from "@/features/players/compare/compare-view";
import { MAX_COMPARE } from "@/features/players/constants";
import { firstParam, parseIds, parseSeason, parseSince } from "@/features/players/format";

export const metadata: Metadata = { title: "Compare players" };

export default async function ComparePage(props: PageProps<"/players/compare">) {
  const sp = await props.searchParams;
  const ids = parseIds(sp.ids, MAX_COMPARE);
  const season = parseSeason(firstParam(sp.season));
  const since = season ? undefined : parseSince(firstParam(sp.since));
  return <CompareView ids={ids} filter={{ season, since }} />;
}
