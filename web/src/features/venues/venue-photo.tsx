import { Camera } from "lucide-react";
import Image from "next/image";
import type { ReactNode } from "react";

import { cn } from "@/lib/utils";

import type { ImageCredit } from "./types";

/**
 * Ground photos (Wikimedia Commons, CC BY / BY-SA / CC0 / PD) served as local WebP crops from
 * /public/venues. They are already sized, so next/image skips the optimizer (`unoptimized`).
 * Every placement shows the attribution the licences require.
 */

/** Plain-text credit, e.g. for a `title` tooltip. */
export function creditText(c: ImageCredit): string {
  return `Photo: ${c.author}, ${c.license} via Wikimedia Commons`;
}

/** "Photo: <author>, <licence> via Wikimedia Commons", linking the file page and the licence. */
export function PhotoCredit({ credit, className }: { credit: ImageCredit; className?: string }) {
  const link = "underline decoration-current/40 underline-offset-2 outline-none hover:decoration-current focus-visible:ring-2 focus-visible:ring-ring";
  return (
    <p className={cn("min-w-0 truncate text-[11px] leading-4", className)} title={creditText(credit)}>
      Photo:{" "}
      <a href={credit.file_page} target="_blank" rel="noopener noreferrer" className={link}>
        {credit.author}
      </a>
      ,{" "}
      {credit.license_url ? (
        <a href={credit.license_url} target="_blank" rel="noopener noreferrer license" className={link}>
          {credit.license}
        </a>
      ) : (
        credit.license
      )}{" "}
      via Wikimedia Commons
    </p>
  );
}

/** Small camera button linking the Commons file page; the credit is its tooltip and label. */
export function PhotoCreditIcon({ credit, className }: { credit: ImageCredit; className?: string }) {
  return (
    <a
      href={credit.file_page}
      target="_blank"
      rel="noopener noreferrer"
      title={creditText(credit)}
      aria-label={creditText(credit)}
      className={cn(
        "inline-flex size-7 items-center justify-center rounded-full bg-black/45 text-white/90 outline-none backdrop-blur-sm hover:bg-black/65 focus-visible:ring-2 focus-visible:ring-ring",
        className,
      )}
    >
      <Camera aria-hidden className="size-3.5" />
    </a>
  );
}

/**
 * Full-width venue banner: the photo bleeds to the edges of <main> (cancels its padding), fades
 * into the page background at the bottom, and carries the title block on a dark scrim so it
 * stays readable in both themes. Leave room below for content that overlaps the bottom edge
 * (the KPI tiles pull up by `HERO_OVERLAP`).
 */
export function VenueHero({
  image,
  credit,
  overline,
  title,
  subtitle,
  topLeft,
}: {
  image: string;
  credit: ImageCredit | null | undefined;
  overline: ReactNode;
  title: ReactNode;
  subtitle?: ReactNode;
  /** e.g. the back link, pinned top-left over the photo. */
  topLeft?: ReactNode;
}) {
  return (
    <header className="relative -mx-4 -mt-5 flex min-h-[200px] flex-col justify-end overflow-hidden px-4 pt-14 pb-10 md:-mx-6 md:min-h-[300px] md:px-6 md:pb-20 lg:min-h-[360px] lg:pb-24">
      <Image src={image} alt="" fill unoptimized loading="eager" fetchPriority="high" sizes="100vw" className="object-cover object-center" />
      {/* Top shade for the chrome pills, bottom fade into the page background. */}
      <div aria-hidden className="absolute inset-0 bg-[linear-gradient(to_bottom,rgb(0_0_0/0.35),transparent_30%,transparent_55%,var(--background)_100%)]" />
      {topLeft && <div className="absolute top-3 left-4 z-10 md:left-6">{topLeft}</div>}
      {credit && (
        <div className="absolute top-3 right-4 z-10 hidden max-w-[min(60%,32rem)] rounded-full bg-black/45 px-2.5 py-1 text-white/90 backdrop-blur-sm md:right-6 md:block">
          <PhotoCredit credit={credit} />
        </div>
      )}
      <div className="relative z-10 w-fit max-w-full rounded-xl bg-black/50 px-4 py-3 text-white shadow-e1 backdrop-blur-[3px] md:px-5 md:py-4">
        <p className="text-overline mb-1 text-white/80">{overline}</p>
        <h1 className="font-display text-[1.75rem] leading-8 font-[650] tracking-[-0.005em] [font-stretch:87.5%] text-balance md:text-[2.5rem] md:leading-[2.75rem] lg:text-5xl lg:leading-[3.25rem]">
          {title}
        </h1>
        {subtitle && <p className="mt-1 text-sm text-white/85">{subtitle}</p>}
        {credit && <PhotoCredit credit={credit} className="mt-1.5 text-white/70 md:hidden" />}
      </div>
    </header>
  );
}

/** Classes for the block right under `VenueHero` so it overlaps the banner's bottom edge. */
export const HERO_OVERLAP = "relative z-10 -mt-6 md:-mt-12 lg:-mt-14";

/** Photo in a card (aspect 16:10) with the credit as a camera-icon tooltip, or a quiet fallback. */
export function VenueThumb({ src, credit, className, children }: { src: string | null | undefined; credit?: ImageCredit | null; className?: string; children?: ReactNode }) {
  return (
    <div className={cn("relative aspect-[16/10] overflow-hidden bg-surface-2", className)}>
      {src ? (
        <Image src={src} alt="" fill unoptimized sizes="(min-width: 1280px) 400px, (min-width: 640px) 50vw, 100vw" className="object-cover" />
      ) : (
        <div aria-hidden className="absolute inset-0 bg-[radial-gradient(120%_90%_at_50%_120%,var(--surface-3),transparent_70%)]" />
      )}
      {children}
      {src && credit && <PhotoCreditIcon credit={credit} className="absolute right-2 bottom-2 z-10" />}
    </div>
  );
}
