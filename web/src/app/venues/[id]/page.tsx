import type { Metadata } from "next";
import { notFound } from "next/navigation";

import { fetchVenue, VENUE_STALE_MS, venueKeys } from "@/features/venues/api";
import { Prefetched } from "@/features/venues/prefetch";
import { VenueDetail } from "@/features/venues/venue-card";

function parseId(raw: string): number | null {
  return /^\d{1,6}$/.test(raw) ? Number(raw) : null;
}

export async function generateMetadata({ params }: { params: Promise<{ id: string }> }): Promise<Metadata> {
  const id = parseId((await params).id);
  if (id === null) return { title: "Venue" };
  try {
    const v = await fetchVenue(id, AbortSignal.timeout(4_000));
    return { title: v.name, description: `Par score, chase and toss bias, phase run rates and records at ${v.name}.` };
  } catch {
    return { title: "Venue" };
  }
}

export default async function VenuePage({ params }: { params: Promise<{ id: string }> }) {
  const id = parseId((await params).id);
  if (id === null) notFound();
  return (
    <Prefetched queries={[{ queryKey: venueKeys.card(id), queryFn: (signal) => fetchVenue(id, signal), staleTime: VENUE_STALE_MS }]}>
      <VenueDetail id={id} />
    </Prefetched>
  );
}
