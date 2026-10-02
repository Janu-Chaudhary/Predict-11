import type { Metadata } from "next";

import { MatchBuilder } from "@/components/builder/match-builder";
import { PageHeader } from "@/components/shell/page-header";

export const metadata: Metadata = {
  title: "Build",
  description: "Build a fantasy XI on the model's honest pre-match predictions (walk-forward), with lock, exclude and re-optimise.",
};

export default async function BuildPage(props: PageProps<"/build">) {
  const sp = await props.searchParams;
  const raw = Array.isArray(sp.match) ? sp.match[0] : sp.match;
  const matchId = raw && /^\d{1,10}$/.test(raw) ? Number(raw) : null;
  return (
    <>
      <PageHeader
        overline="Fantasy builder"
        title="Build your XI"
        subtitle="Start from the XI the model picked before the match, lock or exclude players, and re-optimise on the same predictions."
      />
      <MatchBuilder matchId={matchId} />
    </>
  );
}
