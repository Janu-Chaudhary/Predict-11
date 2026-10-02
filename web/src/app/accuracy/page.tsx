import type { Metadata } from "next";

import { Prefetched } from "@/features/venues/prefetch";
import { DEFAULT_SEASON, PRED_STALE_MS, fetchSeasonPredictions, predKeys } from "@/features/predictions/api";
import { AccuracyView } from "@/features/predictions/accuracy-view";

export const metadata: Metadata = {
  title: "Predictions",
  description: "The XI our model would have picked before every IPL match, predicted using only earlier matches (walk-forward), against what actually happened.",
};

export default async function AccuracyPage(props: PageProps<"/accuracy">) {
  const sp = await props.searchParams;
  const raw = Array.isArray(sp.season) ? sp.season[0] : sp.season;
  const n = Number(raw);
  const year = Number.isInteger(n) && n >= 2008 && n <= 2100 ? n : DEFAULT_SEASON;
  return (
    <Prefetched queries={[{ queryKey: predKeys.season(year), queryFn: (signal) => fetchSeasonPredictions(year, signal), staleTime: PRED_STALE_MS }]}>
      <AccuracyView year={year} />
    </Prefetched>
  );
}
