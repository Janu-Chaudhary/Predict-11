import type { Metadata } from "next";

import { TeamsGrid } from "@/features/season/components/teams-grid";

export const metadata: Metadata = { title: "Teams" };

export default function TeamsPage() {
  return <TeamsGrid />;
}
