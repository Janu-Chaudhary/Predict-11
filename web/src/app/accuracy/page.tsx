import { BarChart3 } from "lucide-react";
import type { Metadata } from "next";

import { EmptyState } from "@/components/shell/empty-state";
import { PageHeader } from "@/components/shell/page-header";

export const metadata: Metadata = { title: "Accuracy" };

export default function AccuracyPage() {
  return (
    <>
      <PageHeader title="Accuracy" subtitle="Public backtest — the trust signal behind every projection." />
      <EmptyState
        icon={BarChart3}
        title="Backtest results coming soon"
        description="Once the model is trained, every season is replayed and scored here, warts and all."
        bullets={[
          "Per-season results vs simple baselines",
          "Captain hit-rate (top-2 captain picks)",
          "Calibration: do the floor–ceiling ranges contain the actual score as often as they claim?",
        ]}
      />
    </>
  );
}
