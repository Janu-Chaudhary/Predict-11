import type { Metadata } from "next";

import { TeamView } from "@/features/season/components/team-view";
import { parseTab, TEAM_TABS } from "@/features/season/tabs";
import { getTeam } from "@/lib/tokens";

type SP = { [key: string]: string | string[] | undefined };
const one = (v: string | string[] | undefined) => (Array.isArray(v) ? v[0] : v);
const int = (v: string | undefined) => (v && /^\d+$/.test(v) ? Number(v) : null);

export async function generateMetadata({ params }: { params: Promise<{ id: string }> }): Promise<Metadata> {
  const { id } = await params;
  const code = decodeURIComponent(id);
  const t = getTeam(code);
  return { title: t.historical || t.name !== code ? t.name : code.toUpperCase() };
}

/** /teams/[id] accepts a short code (RCB) or the numeric team id (46). */
export default async function TeamPage({ params, searchParams }: { params: Promise<{ id: string }>; searchParams: Promise<SP> }) {
  const [{ id }, sp] = await Promise.all([params, searchParams]);
  return (
    <TeamView
      slug={id}
      tab={parseTab(sp.tab, TEAM_TABS, "overview")}
      initialSeason={int(one(sp.season))}
      initialVs={one(sp.vs) ?? null}
      initialVenue={int(one(sp.venue))}
    />
  );
}
