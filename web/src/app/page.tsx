import { HomeView } from "@/features/home/home-view";
import { parsePreview } from "@/features/home/lib/rotation";
import { loadHome } from "@/features/home/server";

// Hero rotation depends on "now" (match state), so render per request.
export const dynamic = "force-dynamic";

export default async function HomePage({ searchParams }: PageProps<"/">) {
  const sp = await searchParams;
  const data = await loadHome(parsePreview(sp.hero));
  return <HomeView data={data} />;
}
