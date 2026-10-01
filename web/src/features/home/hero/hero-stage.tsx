import type { ResolvedHero } from "../types";
import { WagonHero } from "./wagon-hero";
import { WormHero } from "./worm-hero";
import { XIHero } from "./xi-hero";

/** Renders whichever hero the rotation resolved to (A wagon, B XI, C worm). */
export function HeroStage({ hero }: { hero: ResolvedHero }) {
  switch (hero.kind) {
    case "A":
      return <WagonHero wagon={hero.wagon} match={hero.match} note={hero.note} />;
    case "B":
      return <XIHero xi={hero.xi} match={hero.match} note={hero.note} />;
    case "C":
      return <WormHero worm={hero.worm} note={hero.note} />;
    default:
      return (
        <div className="grid aspect-[358/300] w-full place-items-center rounded-2xl border border-dashed border-border text-sm text-muted-foreground sm:aspect-[16/10]">
          {hero.note || "Nothing to draw yet."}
        </div>
      );
  }
}
