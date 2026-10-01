import { HeroStage } from "./hero/hero-stage";
import { Bento } from "./bento";
import { MatchCard } from "./match-card";
import type { HomeData } from "./types";

/** Home (§4.1): rotating data hero beside the next-match card, then the explore bento. */
export function HomeView({ data }: { data: HomeData }) {
  return (
    <>
      <h1 className="sr-only">Predict-11 home</h1>
      {data.error || !data.state ? (
        <div role="alert" className="rounded-2xl border border-border bg-card p-5">
          <p className="font-semibold">Couldn&apos;t load the home page data.</p>
          <p className="mt-1 text-sm text-muted-foreground">{data.error} Reload to try again.</p>
        </div>
      ) : (
        <div className="grid items-center gap-5 lg:grid-cols-[1.25fr_1fr] lg:gap-8">
          <HeroStage hero={data.hero} />
          <MatchCard state={data.state} />
        </div>
      )}
      <Bento tiles={data.tiles} />
    </>
  );
}
