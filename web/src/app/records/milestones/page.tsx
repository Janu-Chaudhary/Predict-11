import type { Metadata } from "next";

import { CURRENT_SEASON } from "@/lib/seasons";
import { PageHeader } from "@/components/shell/page-header";
import { fetchMilestones, recordKeys, RECORDS_STALE_MS } from "@/features/milestones/api";
import { RecordsSeasonSelect } from "@/features/milestones/controls";
import { MilestonesWatch } from "@/features/milestones/milestones-watch";
import { RunningStreaksRail } from "@/features/milestones/records-rails";
import { RecordsSubnav } from "@/features/milestones/records-subnav";
import { parseSeason, Prefetched } from "@/features/venues/prefetch";

export const metadata: Metadata = {
  title: "Milestones watch",
  description: "Players closing in on round-number IPL career milestones.",
};

export default async function MilestonesPage({ searchParams }: { searchParams: Promise<Record<string, string | string[] | undefined>> }) {
  const season = parseSeason((await searchParams).season);
  return (
    <>
      <PageHeader
        overline="Records"
        title="Milestones watch"
        subtitle="Who is about to reach a round-number IPL career total: runs, wickets, sixes, catches and appearances."
        actions={<RecordsSeasonSelect value={season ?? CURRENT_SEASON} />}
      />
      <RecordsSubnav active="milestones" season={season} />
      <Prefetched queries={[{ queryKey: recordKeys.milestones(season), queryFn: (s) => fetchMilestones(season, s), staleTime: RECORDS_STALE_MS }]}>
        <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_26rem] xl:gap-5">
          <div className="min-w-0">
            <MilestonesWatch season={season} />
          </div>
          <aside aria-label="Related records" className="grid content-start gap-4 xl:sticky xl:top-20 xl:self-start">
            <RunningStreaksRail season={season} />
          </aside>
        </div>
      </Prefetched>
    </>
  );
}
