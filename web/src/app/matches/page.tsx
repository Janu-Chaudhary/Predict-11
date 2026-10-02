import { CalendarDays } from "lucide-react";
import type { Metadata } from "next";

import { CURRENT_SEASON } from "@/lib/seasons";
import { EmptyState } from "@/components/shell/empty-state";
import { PageHeader } from "@/components/shell/page-header";

import { MatchesSeasonSelect } from "./season-switch";

export const metadata: Metadata = { title: "Matches" };

export default function MatchesPage() {
  return (
    <>
      <PageHeader
        overline={`IPL ${CURRENT_SEASON}`}
        title="Matches"
        subtitle="Fixtures and results, with how fresh each projection is."
        actions={<MatchesSeasonSelect />}
      />
      <EmptyState
        icon={CalendarDays}
        title="No fixtures loaded yet"
        why="The fixtures feed isn’t wired to this page yet, so there is nothing to list. IPL 2026 has finished; the 2027 schedule is usually published in February–March."
        when="As soon as the fixtures endpoint lands, this page fills itself; no refresh needed."
        action={{ href: "/table", label: "See the points table" }}
        bullets={[
          "Date strip with “Today”, team filter and season switch",
          "Each match shows its state: Provisional · XI confirmed ✓ 19:02 · Awaiting result · Reviewed",
          "Results link straight into the match centre (summary, scorecard, fantasy, review)",
        ]}
      />
    </>
  );
}
