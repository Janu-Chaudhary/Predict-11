import type { Metadata } from "next";

import { PageHeader } from "@/components/shell/page-header";
import { PlayersIndex } from "@/features/players/players-index";

export const metadata: Metadata = { title: "Players" };

export default function PlayersPage() {
  return (
    <>
      <PageHeader overline="Explore" title="Players" subtitle="Career and season stats, phase splits, form and matchups for every IPL player since 2008." />
      <PlayersIndex />
    </>
  );
}
