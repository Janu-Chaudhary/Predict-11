import Link from "next/link";
import type { ReactNode } from "react";

import { TabLinks } from "@/components/shell/tab-links";
import { cn } from "@/lib/utils";

import { categoryShares } from "./format";
import type { CategoryMix } from "./types";

/** Sibling navigation: leaderboards ⇄ best XIs. */
export function FantasySubnav({ active, season }: { active: "leaderboards" | "best-xi"; season?: number | null }) {
  const qs = season ? `?season=${season}` : "";
  return (
    <TabLinks
      label="Fantasy sections"
      active={active}
      tabs={[
        { key: "leaderboards", label: "Leaderboards" },
        { key: "best-xi", label: "Best XI" },
      ]}
      hrefFor={(k) => (k === "leaderboards" ? `/fantasy${qs}` : `/fantasy/best-xi${qs}`)}
    />
  );
}

/** Segmented control (single choice). Buttons with aria-pressed; 36 px tall, scrolls inside itself. */
export function Segmented<T extends string>({
  label,
  options,
  value,
  onChange,
  className,
}: {
  label: string;
  options: { key: T; label: ReactNode; title?: string }[];
  value: T;
  onChange: (v: T) => void;
  className?: string;
}) {
  return (
    <div role="group" aria-label={label} className={cn("no-scrollbar inline-flex max-w-full overflow-x-auto rounded-[10px] bg-surface-2 p-0.5", className)}>
      {options.map((o) => (
        <button
          key={o.key}
          type="button"
          title={o.title}
          aria-pressed={value === o.key}
          onClick={() => onChange(o.key)}
          className={cn(
            "inline-flex h-9 shrink-0 items-center rounded-lg px-3 text-sm font-medium whitespace-nowrap text-muted-foreground outline-none hover:text-foreground focus-visible:ring-2 focus-visible:ring-ring",
            value === o.key && "bg-card text-foreground shadow-e1",
          )}
        >
          {o.label}
        </button>
      ))}
    </div>
  );
}

/** Stacked bar of mean points by category, with a printed legend (colour is never the only cue). */
export function CategoryMixBar({ mix, className }: { mix: CategoryMix | null; className?: string }) {
  const shares = categoryShares(mix);
  if (shares.length === 0) return <p className="text-sm text-muted-foreground">No category breakdown yet.</p>;
  const label = `Where the points come from: ${shares.map((s) => `${s.label} ${Math.round(s.pct)}%`).join(", ")}`;
  return (
    <div className={className}>
      <div role="img" aria-label={label} className="flex h-2.5 w-full gap-0.5 overflow-hidden rounded-full bg-surface-3">
        {shares.map((s) => (
          <span key={s.key} className={cn("h-full first:rounded-l-full last:rounded-r-full", s.cls)} style={{ width: `${s.pct}%` }} />
        ))}
      </div>
      <ul aria-hidden className="num mt-2 flex flex-wrap gap-x-3 gap-y-1 text-xs text-muted-foreground">
        {shares.map((s) => (
          <li key={s.key} className="inline-flex items-center gap-1.5">
            <span className={cn("size-2 rounded-full", s.cls)} />
            {s.label} <span className="font-semibold text-foreground">{Math.round(s.pct)}%</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

export function ToolLink({ href, children, className }: { href: string; children: ReactNode; className?: string }) {
  return (
    <Link
      href={href}
      className={cn(
        "inline-flex h-10 items-center gap-1.5 rounded-[10px] border border-border bg-card px-3 text-sm font-medium outline-none hover:bg-surface-2 focus-visible:ring-2 focus-visible:ring-ring",
        className,
      )}
    >
      {children}
    </Link>
  );
}
