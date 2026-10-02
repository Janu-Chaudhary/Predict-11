"use client";

import Image from "next/image";
import { useState } from "react";

import { getTeam } from "@/lib/tokens";
import { cn } from "@/lib/utils";

const PX = { xs: 24, sm: 32, md: 40, lg: 56, xl: 80, "2xl": 120, hero: 176 } as const;
export type PlayerAvatarSize = keyof typeof PX;

export function initials(name: string) {
  const parts = name.split(/\s+/).filter(Boolean);
  if (parts.length === 0) return "?";
  const first = parts[0][0] ?? "";
  const last = parts.length > 1 ? parts[parts.length - 1][0] : "";
  return (first + last).toUpperCase();
}

/** Locally cached photo written by `p11 media cache`: /players/<id>-{256,96}.webp. */
const LOCAL_PHOTO = /^\/players\/([^/]+)-(256|96)\.webp$/;

/**
 * Pick the photo to load. Local cached WebPs are already small and square, so they skip the
 * Next optimizer and use the 96 px variant when that still covers 2x DPR; remote URLs (official
 * IPL hosts, ~1 MB PNG, slow) go through next/image.
 */
export function photoSource(src: string, px: number): { src: string; local: boolean } {
  const m = LOCAL_PHOTO.exec(src);
  if (!m) return { src, local: false };
  return { src: `/players/${m[1]}-${px * 2 <= 96 ? 96 : 256}.webp`, local: true };
}

/**
 * Player photo. The official headshots are transparent cut-outs, so a photo is drawn frameless
 * (no circle, ring or fill) straight on the page background, bottom-aligned in its square box.
 * Prefers the API's `image_url`, which is the locally cached WebP when available; lazy-loaded
 * with a skeleton until loaded. No URL or a load error → initials in a circle with a team-colour
 * ring. Decorative by default (`alt=""`) because the name is always printed next to it.
 */
export function PlayerAvatar({
  name,
  src,
  team,
  size = "sm",
  alt = "",
  eager = false,
  className,
}: {
  name: string;
  src?: string | null;
  team?: string;
  size?: PlayerAvatarSize;
  alt?: string;
  /** Load immediately (above-the-fold profile header). Default lazy. */
  eager?: boolean;
  className?: string;
}) {
  const px = PX[size];
  const [state, setState] = useState<"loading" | "loaded" | "error">("loading");
  // Reset when the photo changes (render-phase sync, no effect needed).
  const [prevSrc, setPrevSrc] = useState(src);
  if (prevSrc !== src) {
    setPrevSrc(src);
    setState("loading");
  }
  const ring = team ? getTeam(team).primary : "var(--border)";
  const showImage = Boolean(src) && state !== "error";
  const photo = src ? photoSource(src, px) : null;

  return (
    <span
      role={alt ? "img" : undefined}
      aria-label={alt || undefined}
      aria-hidden={alt ? undefined : true}
      data-state={showImage ? state : "fallback"}
      className={cn("relative inline-flex shrink-0 items-end justify-center", !showImage && "overflow-hidden rounded-full bg-surface-3", className)}
      style={{ width: px, height: px, boxShadow: showImage ? undefined : `0 0 0 ${px >= 40 ? 2 : 1.5}px ${ring}` }}
    >
      {showImage ? (
        <>
          {state === "loading" && <span className="sk absolute inset-0 rounded-lg" />}
          <Image
            src={photo!.src}
            unoptimized={photo!.local}
            alt=""
            width={px}
            height={px}
            loading={eager ? "eager" : "lazy"}
            onLoad={() => setState("loaded")}
            onError={() => setState("error")}
            className={cn(
              "size-full object-contain object-bottom transition-opacity duration-200 motion-reduce:transition-none",
              state === "loaded" ? "opacity-100" : "opacity-0",
            )}
          />
        </>
      ) : (
        <span
          className="font-condensed leading-none font-bold text-muted-foreground select-none"
          style={{ fontSize: Math.max(11, Math.round(px * 0.38)) }}
        >
          {initials(name)}
        </span>
      )}
    </span>
  );
}
