import type { Metadata } from "next";
import { notFound } from "next/navigation";

import { SeasonView } from "@/features/season/components/season-view";
import { parseTab, SEASON_TABS } from "@/features/season/tabs";

const FIRST = 2008;
const LAST = 2026;

function parseSeason(raw: string): number | null {
  const n = Number(raw);
  return Number.isInteger(n) && n >= FIRST && n <= LAST ? n : null;
}

export async function generateMetadata({ params }: { params: Promise<{ season: string }> }): Promise<Metadata> {
  const { season } = await params;
  return { title: `Points table · IPL ${season}` };
}

export default async function SeasonTablePage({
  params,
  searchParams,
}: {
  params: Promise<{ season: string }>;
  searchParams: Promise<{ [key: string]: string | string[] | undefined }>;
}) {
  const [{ season: raw }, sp] = await Promise.all([params, searchParams]);
  const season = parseSeason(raw);
  if (season === null) notFound();
  const tab = parseTab(sp.tab, SEASON_TABS, "table");
  const afterRaw = Array.isArray(sp.after) ? sp.after[0] : sp.after;
  const after = afterRaw !== undefined && /^\d+$/.test(afterRaw) ? Number(afterRaw) : null;
  return <SeasonView season={season} tab={tab} after={after} />;
}
