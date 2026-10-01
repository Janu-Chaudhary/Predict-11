import type { Metadata } from "next";

import { MoreList } from "@/components/shell/nav";
import { PageHeader } from "@/components/shell/page-header";

export const metadata: Metadata = { title: "More" };

export default function MorePage() {
  return (
    <>
      <PageHeader title="More" subtitle="Explore teams, players, venues, records and how accurate the model is." />
      <MoreList />
    </>
  );
}
