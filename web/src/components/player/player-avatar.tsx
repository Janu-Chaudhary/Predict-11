"use client";

import Image from "next/image";
import { useState } from "react";

import { getTeam } from "@/lib/tokens";
import { cn } from "@/lib/utils";

const PX = { xs: 24, sm: 32, md: 40, lg: 56, xl: 80 } as const;
export type PlayerAvatarSize = keyof typeof PX;

export function initials(name: string) {
  const parts = name.split(/\s+/).filter(Boolean);
  if (parts.length === 0) return "?";
  const first = parts[0][0] ?? "";
  const last = parts.length > 1 ? parts[parts.length - 1][0] : "";
  return (first + last).toUpperCase();
}

/**
 * Circular player photo with a team-colour ring. Remote photos (official IPL hosts) go through
 * next/image, so Next resizes/caches the ~1 MB originals; lazy-loaded with a floodlight-sweep
 * skeleton until loaded. No URL or a load error → initials on surface-3.
 * Decorative by default (`alt=""`) because the name is always printed next to it.
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

  return (
    <span
      role={alt ? "img" : undefined}
      aria-label={alt || undefined}
      aria-hidden={alt ? undefined : true}
      data-state={showImage ? state : "fallback"}
      className={cn("relative inline-flex shrink-0 items-center justify-center overflow-hidden rounded-full bg-surface-3", className)}
      style={{ width: px, height: px, boxShadow: `0 0 0 ${px >= 40 ? 2 : 1.5}px ${ring}` }}
    >
      {showImage ? (
        <>
          {state === "loading" && <span className="sk absolute inset-0 rounded-full" />}
          <Image
            src={src!}
            alt=""
            width={px}
            height={px}
            loading={eager ? "eager" : "lazy"}
            onLoad={() => setState("loaded")}
            onError={() => setState("error")}
            className={cn(
              "size-full object-cover object-top transition-opacity duration-200 motion-reduce:transition-none",
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
