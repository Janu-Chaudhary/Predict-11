import { Target } from "lucide-react";
import type { Metadata } from "next";

import { EmptyState } from "@/components/shell/empty-state";
import { PageHeader } from "@/components/shell/page-header";

export const metadata: Metadata = { title: "Accuracy" };

export default function AccuracyPage() {
  return (
    <>
      <PageHeader overline="Trust" title="Accuracy" subtitle="The public backtest behind every projection, warts and all." />
      <EmptyState
        icon={Target}
        title="Backtest results not published yet"
        why="The projection model hasn’t been backtested, so there is nothing honest to show."
        when="After the model is trained, every season is replayed and scored here."
        action={{ href: "/matches", label: "Browse matches" }}
        bullets={[
          "Per-season results vs simple baselines",
          "Captain hit-rate (top-2 captain picks)",
          "Calibration: do the floor–ceiling ranges contain the actual score as often as they claim?",
        ]}
      />
    </>
  );
}
