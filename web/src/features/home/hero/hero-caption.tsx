import type { ReactNode } from "react";

export function LegendDot({ colour, line = false, children }: { colour: string; line?: boolean; children: ReactNode }) {
  return (
    <span className="inline-flex items-center gap-1">
      <i
        aria-hidden
        className={line ? "inline-block h-0.5 w-3.5 rounded-full" : "inline-block size-[7px] rounded-full"}
        style={{ background: colour }}
      />
      {children}
    </span>
  );
}

/** Caption under a hero visual: what it shows, a colour legend, and why this hero was picked. */
export function HeroCaption({ lead, legend, note }: { lead: ReactNode; legend?: ReactNode; note?: string }) {
  return (
    <figcaption className="mt-2.5 grid justify-items-center gap-1 text-center text-xs text-muted-foreground">
      <span className="flex flex-wrap items-center justify-center gap-x-3.5 gap-y-1.5">
        <span>{lead}</span>
        {legend && <span className="inline-flex flex-wrap gap-2.5">{legend}</span>}
      </span>
      {note && <span className="text-faint">{note}</span>}
    </figcaption>
  );
}
