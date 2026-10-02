import type { Metadata } from "next";

import { PageHeader } from "@/components/shell/page-header";
import { fetchStreaks, recordKeys, RECORDS_STALE_MS } from "@/features/milestones/api";
import { RecordsSeasonSelect } from "@/features/milestones/controls";
import { ClosestMilestonesRail } from "@/features/milestones/records-rails";
import { RecordsSubnav } from "@/features/milestones/records-subnav";
import { Streaks } from "@/features/milestones/streaks-board";
import { parseSeason, Prefetched } from "@/features/venues/prefetch";

export const metadata: Metadata = {
  title: "Streaks",
  description: "Current and longest IPL streaks: consecutive 30+ scores, wickets in consecutive innings, innings without a duck.",
};

export default async function StreaksPage({ searchParams }: { searchParams: Promise<Record<string, string | string[] | undefined>> }) {
  const sp = await searchParams;
  const season = parseSeason(sp.season);
  const type = Array.isArray(sp.type) ? sp.type[0] : sp.type;
  return (
    <>
      <PageHeader
        overline="Records"
        title="Streaks"
        subtitle="Who is on a run right now, and the longest runs on record: 30+ scores, wickets in consecutive innings, innings without a duck."
        actions={<RecordsSeasonSelect value={season} allLabel="All seasons" />}
      />
      <RecordsSubnav active="streaks" season={season} />
      <Prefetched queries={[{ queryKey: recordKeys.streaks(season), queryFn: (s) => fetchStreaks(season, s), staleTime: RECORDS_STALE_MS }]}>
        <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_26rem] xl:gap-5">
          <div className="min-w-0">
            <Streaks season={season} initialType={type} />
          </div>
          <aside aria-label="Related records" className="grid content-start gap-4 xl:sticky xl:top-20 xl:self-start">
            <ClosestMilestonesRail season={season} />
          </aside>
        </div>
      </Prefetched>
    </>
  );
}
