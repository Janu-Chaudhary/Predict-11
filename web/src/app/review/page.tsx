import { ClipboardCheck } from "lucide-react";
import type { Metadata } from "next";

import { EmptyState } from "@/components/shell/empty-state";
import { PageHeader } from "@/components/shell/page-header";

export const metadata: Metadata = { title: "Review" };

export default function ReviewPage() {
  return (
    <>
      <PageHeader title="Review" subtitle="How the projections did, roughly an hour after each match." />
      <EmptyState
        icon={ClipboardCheck}
        title="No completed matches to review"
        description="Post-match reviews land about an hour after the final ball, once the scorecard is scraped."
        bullets={[
          "Predicted vs actual fantasy points for every player",
          "Your XI’s rank against thousands of simulated XIs",
          "Rate My Team: paste or build an XI → projected percentile + best swaps",
        ]}
      />
    </>
  );
}
