import type { Metadata } from "next";

import { firstParam, parseSeason, parseSince } from "@/features/players/format";
import { PROFILE_TABS, type ProfileTab } from "@/features/players/constants";
import { ProfileView } from "@/features/players/profile/profile-view";

export const metadata: Metadata = { title: "Player" };

export default async function PlayerPage(props: PageProps<"/players/[id]">) {
  const { id } = await props.params;
  const sp = await props.searchParams;
  const rawTab = firstParam(sp.tab);
  const tab: ProfileTab = PROFILE_TABS.includes(rawTab as ProfileTab) ? (rawTab as ProfileTab) : "overview";
  const season = parseSeason(firstParam(sp.season));
  const since = season ? undefined : parseSince(firstParam(sp.since));
  return <ProfileView id={decodeURIComponent(id)} tab={tab} filter={{ season, since }} />;
}
