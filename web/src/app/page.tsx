import { CalendarDays } from "lucide-react";

import { EmptyState } from "@/components/shell/empty-state";
import { PageHeader } from "@/components/shell/page-header";

export default function FixturesPage() {
  return (
    <>
      <PageHeader title="Fixtures" subtitle="Upcoming IPL matches and how fresh each projection is." />
      <EmptyState
        icon={CalendarDays}
        title="No fixtures yet"
        description="Fixtures appear here once the ingestion pipeline is scheduling matches."
        bullets={[
          "Fixture list with a data-freshness badge: “Pre-toss projection” vs “Lineups confirmed ✓ 19:02”",
          "Auto re-projection at toss / XI announcement, with a notification",
          "Pitch & conditions card: par score, pace/spin split, chase bias, dew/weather",
          "Impact-player intelligence: likely 12th man / likely subbed-out",
          "Short match preview generated only from structured features",
        ]}
      />
    </>
  );
}
