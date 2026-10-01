import type { SVGProps } from "react";

/**
 * Custom cricket glyphs in lucide's grammar: 24 px grid, 1.75 stroke, round caps, currentColor.
 * §2.6 — used for role chips and cricket-specific affordances (no emoji anywhere).
 */
type IconProps = SVGProps<SVGSVGElement> & { size?: number };

function Glyph({ size = 20, children, ...props }: IconProps & { children: React.ReactNode }) {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.75}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden
      {...props}
    >
      {children}
    </svg>
  );
}

export function BatIcon(props: IconProps) {
  return (
    <Glyph {...props}>
      <path d="M14.5 9.5 5.6 18.4a1.9 1.9 0 0 1-2.7-2.7L11.8 6.8" />
      <path d="m11.8 6.8 2.7-2.7 5.4 5.4-2.7 2.7" />
      <path d="m19.2 4.8 1.8-1.8" />
    </Glyph>
  );
}

export function BallIcon(props: IconProps) {
  return (
    <Glyph {...props}>
      <circle cx="12" cy="12" r="8" />
      <path d="M9 4.6c2.2 2 2.2 12.8 0 14.8" />
      <path d="M15 4.6c-2.2 2-2.2 12.8 0 14.8" />
    </Glyph>
  );
}

export function StumpsIcon(props: IconProps) {
  return (
    <Glyph {...props}>
      <path d="M7 8v13M12 8v13M17 8v13" />
      <path d="M6 5h5M13 5h5" />
    </Glyph>
  );
}

export function GlovesIcon(props: IconProps) {
  return (
    <Glyph {...props}>
      <path d="M7 21v-4.5L4.5 13a1.6 1.6 0 0 1 2.4-2.1L8 12V5.5a1.5 1.5 0 0 1 3 0V11" />
      <path d="M11 5a1.5 1.5 0 0 1 3 0v6" />
      <path d="M14 6a1.5 1.5 0 0 1 3 0v5.5" />
      <path d="M17 8.5a1.5 1.5 0 0 1 3 0V15a6 6 0 0 1-6 6H7" />
    </Glyph>
  );
}

export function AllRounderIcon(props: IconProps) {
  return (
    <Glyph {...props}>
      <path d="M12.5 11.5 5.6 18.4a1.9 1.9 0 0 1-2.7-2.7l6.9-6.9" />
      <path d="m9.8 8.8 2.4-2.4 3.4 3.4-2.4 2.4" />
      <circle cx="17.5" cy="17.5" r="3.5" />
    </Glyph>
  );
}
