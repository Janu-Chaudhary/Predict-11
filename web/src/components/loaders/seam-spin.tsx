import { useId } from "react";

import { cn } from "@/lib/utils";

/**
 * Seam spin — the app-level loader (§7.2 #1). A white T20 ball whose seam rotates about the
 * vertical axis, with a slight tilt sway. Pure SVG + CSS; reduced motion → static ball with a pulse.
 * Server-safe (no hooks beyond useId), so it can render in `loading.tsx`.
 */
export function SeamSpin({
  label = "Loading match data",
  size = 56,
  className,
}: {
  label?: string;
  size?: number;
  className?: string;
}) {
  const uid = useId().replace(/:/g, "");
  const shade = `seam-shade-${uid}`;
  const clip = `seam-clip-${uid}`;
  return (
    <div role="status" aria-live="polite" className={cn("seam-loader grid justify-items-center gap-3.5", className)}>
      <div className="seam-ball-wrap">
        <svg viewBox="-30 -30 60 60" width={size} height={size} aria-hidden>
          <defs>
            <radialGradient id={shade} cx="35%" cy="30%" r="75%">
              <stop offset="0" stopColor="#fff" stopOpacity="0" />
              <stop offset="1" stopColor="#1b2036" stopOpacity="0.35" />
            </radialGradient>
            <clipPath id={clip}>
              <circle r="26" />
            </clipPath>
          </defs>
          <circle r="26" fill="oklch(0.96 0.01 90)" />
          <g clipPath={`url(#${clip})`}>
            <g className="seam-ball-seam" fill="none" stroke="oklch(0.62 0.2 25)">
              <path strokeWidth="2.2" d="M -6,-26 C 6,-12 6,12 -6,26" />
              <path strokeWidth="2.2" d="M 2,-26 C 14,-12 14,12 2,26" />
              <path strokeWidth="1.2" strokeDasharray="1.2 2.4" opacity="0.85" d="M -9,-26 C 3,-12 3,12 -9,26" />
              <path strokeWidth="1.2" strokeDasharray="1.2 2.4" opacity="0.85" d="M 5,-26 C 17,-12 17,12 5,26" />
            </g>
          </g>
          <circle r="26" fill={`url(#${shade})`} />
        </svg>
      </div>
      <span className="text-xs font-medium tracking-[0.04em] text-muted-foreground">
        {label}
        <span aria-hidden className="loader-dots inline-block w-3 text-left" />
      </span>
    </div>
  );
}
