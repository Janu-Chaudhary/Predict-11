import type { ReactNode } from "react";

/**
 * Profile tab layout: an optional full-width band (headline tiles), then main column + side rail
 * (8 / 4 on desktop), then an optional full-width footer band. Single column on mobile.
 */
export function ProfileLayout({ band, main, rail, footer }: { band?: ReactNode; main: ReactNode; rail: ReactNode; footer?: ReactNode }) {
  return (
    <div className="grid grid-cols-1 gap-4 lg:gap-6">
      {band}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-12 lg:gap-6">
        <div className="grid min-w-0 grid-cols-1 content-start gap-4 lg:col-span-8 lg:gap-6">{main}</div>
        <aside className="grid min-w-0 grid-cols-1 content-start gap-4 lg:col-span-4" aria-label="Player side panel">
          {rail}
        </aside>
      </div>
      {footer}
    </div>
  );
}
