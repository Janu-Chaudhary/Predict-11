import type { Metadata } from "next";

import { RecordsView } from "@/features/season/components/records-view";

export const metadata: Metadata = { title: "Records" };

const one = (v: string | string[] | undefined) => (Array.isArray(v) ? v[0] : v);
const int = (v: string | undefined) => (v && /^\d+$/.test(v) ? Number(v) : null);

export default async function RecordsPage({ searchParams }: { searchParams: Promise<{ [key: string]: string | string[] | undefined }> }) {
  const sp = await searchParams;
  const season = int(one(sp.season));
  return <RecordsView initialSeason={season && season >= 2008 && season <= 2026 ? season : null} initialVenue={int(one(sp.venue))} />;
}
