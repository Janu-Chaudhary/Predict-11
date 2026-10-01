import type { Metadata } from "next";

import { PageHeader } from "@/components/shell/page-header";
import { fetchVenues, VENUE_STALE_MS, venueKeys } from "@/features/venues/api";
import { Prefetched } from "@/features/venues/prefetch";
import { VenueList } from "@/features/venues/venue-list";

export const metadata: Metadata = { title: "Venues" };

export default function VenuesPage() {
  return (
    <>
      <PageHeader overline="Explore" title="Venues" subtitle="Par scores, chase bias and toss trends for every IPL ground. Tap a venue for its full card." />
      <Prefetched queries={[{ queryKey: venueKeys.list, queryFn: fetchVenues, staleTime: VENUE_STALE_MS }]}>
        <VenueList />
      </Prefetched>
    </>
  );
}
