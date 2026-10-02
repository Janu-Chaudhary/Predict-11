import Image from "next/image";
import Link from "next/link";

import type { HomeMatch } from "@/features/home/types";
import { getJson } from "@/features/venues/api";
import { PhotoCredit } from "@/features/venues/venue-photo";

/** Match header facts from GET /home/match/{id}; null when the id is unknown or the API is down. */
export async function fetchMatchHeader(id: string): Promise<HomeMatch | null> {
  if (!/^\d{1,10}$/.test(id)) return null;
  try {
    return await getJson<HomeMatch>(`/home/match/${id}`, AbortSignal.timeout(4_000));
  } catch {
    return null;
  }
}

/**
 * Ground photo band across the top of the match header card (fades into the card), with the
 * venue name and the photo credit the licence requires. Renders nothing without a photo.
 */
export function MatchVenueBanner({ match }: { match: HomeMatch }) {
  const v = match.venue;
  if (!v?.image_url) return null;
  const when = new Date(match.date).toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric" });
  return (
    <div className="relative -mx-4 -mt-4 mb-1 flex h-40 flex-col justify-end overflow-hidden rounded-t-xl px-4 pb-3 md:h-56">
      <Image src={v.image_url} alt="" fill unoptimized loading="eager" sizes="100vw" className="object-cover" />
      <div aria-hidden className="absolute inset-0 bg-[linear-gradient(to_bottom,transparent_35%,var(--card)_100%)]" />
      <div className="relative z-10 flex flex-wrap items-end justify-between gap-2">
        <div className="w-fit max-w-full rounded-lg bg-black/50 px-3 py-2 text-white backdrop-blur-[3px]">
          <p className="text-overline text-white/80">
            {match.title} · IPL {match.season} · <span className="num">{when}</span>
          </p>
          <Link href={`/venues/${v.id}`} className="font-display text-lg leading-6 font-semibold [font-stretch:87.5%] outline-none hover:underline focus-visible:ring-2 focus-visible:ring-ring md:text-xl">
            {v.name}
            {v.city ? <span className="font-sans text-sm font-normal text-white/80">, {v.city}</span> : null}
          </Link>
        </div>
        {v.image_credit && (
          <div className="max-w-full rounded-full bg-black/45 px-2.5 py-1 text-white/90 backdrop-blur-sm md:max-w-[50%]">
            <PhotoCredit credit={v.image_credit} />
          </div>
        )}
      </div>
    </div>
  );
}
