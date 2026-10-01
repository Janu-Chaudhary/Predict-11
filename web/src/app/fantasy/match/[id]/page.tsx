import type { Metadata } from "next";
import { notFound } from "next/navigation";

import { FANTASY_STALE_MS, fantasyKeys, fetchMatchBestXi } from "@/features/fantasy/api";
import { MatchXiView } from "@/features/fantasy/match-xi-view";
import { Prefetched } from "@/features/venues/prefetch";

export const metadata: Metadata = { title: "Match best XI", description: "Hindsight Dream Team for one IPL match against the pick-on-form XI." };

export default async function MatchXiPage({ params }: { params: Promise<{ id: string }> }) {
  const raw = (await params).id;
  if (!/^\d{1,9}$/.test(raw)) notFound();
  const id = Number(raw);
  return (
    <Prefetched queries={[{ queryKey: fantasyKeys.matchXi(id), queryFn: (signal) => fetchMatchBestXi(id, signal), staleTime: FANTASY_STALE_MS }]}>
      <MatchXiView id={id} />
    </Prefetched>
  );
}
