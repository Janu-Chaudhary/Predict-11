import type { ReactNode } from "react";

import { cn } from "@/lib/utils";

/** One `<h1>` per page: Saira display, solid colour, optional overline and actions. */
export function PageHeader({
  title,
  subtitle,
  overline,
  actions,
  className,
}: {
  title: ReactNode;
  subtitle?: ReactNode;
  overline?: ReactNode;
  actions?: ReactNode;
  className?: string;
}) {
  return (
    <div className={cn("mb-6 flex flex-wrap items-end justify-between gap-3", className)}>
      <div className="min-w-0">
        {overline && <p className="text-overline mb-1 text-muted-foreground">{overline}</p>}
        <h1 className="text-display text-foreground">{title}</h1>
        {subtitle && <p className="mt-1 max-w-prose text-sm text-muted-foreground">{subtitle}</p>}
      </div>
      {actions && <div className="flex shrink-0 items-center gap-2">{actions}</div>}
    </div>
  );
}

/** Section heading inside a page (overline style, optional trailing link). */
export function SectionHeader({ title, action, id }: { title: ReactNode; action?: ReactNode; id?: string }) {
  return (
    <div className="mb-2 flex items-center justify-between gap-2">
      <h2 id={id} className="text-overline text-muted-foreground">
        {title}
      </h2>
      {action}
    </div>
  );
}
