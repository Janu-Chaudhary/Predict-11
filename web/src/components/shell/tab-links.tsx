import Link from "next/link";

import { cn } from "@/lib/utils";

export type TabLink = { key: string; label: string; disabled?: boolean };

/**
 * URL-driven tabs (`?tab=`): shareable and back-button friendly (§3.1). Horizontally scrollable
 * with an edge fade on mobile; the active tab carries a 2 px violet underline.
 */
export function TabLinks({
  tabs,
  active,
  hrefFor,
  label,
  className,
}: {
  tabs: TabLink[];
  active: string;
  hrefFor: (key: string) => string;
  label: string;
  className?: string;
}) {
  return (
    <nav aria-label={label} className={cn("relative -mx-4 mb-4 border-b border-border md:mx-0", className)}>
      <ul className="no-scrollbar flex gap-1 overflow-x-auto px-4 [mask-image:linear-gradient(90deg,#000_90%,transparent)] md:px-0 md:[mask-image:none]">
        {tabs.map((t) => {
          const isActive = t.key === active;
          return (
            <li key={t.key} className="shrink-0">
              <Link
                href={hrefFor(t.key)}
                scroll={false}
                aria-current={isActive ? "page" : undefined}
                className={cn(
                  "relative flex h-11 items-center px-3 text-sm font-medium whitespace-nowrap text-muted-foreground outline-none hover:text-foreground focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-inset",
                  isActive && "text-foreground",
                  t.disabled && "text-faint",
                )}
              >
                {t.label}
                {isActive && <span aria-hidden className="absolute inset-x-3 -bottom-px h-0.5 rounded-full bg-brand" />}
              </Link>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}

export function pickTab<T extends string>(value: string | string[] | undefined, tabs: readonly T[], fallback: T): T {
  const v = Array.isArray(value) ? value[0] : value;
  return tabs.includes(v as T) ? (v as T) : fallback;
}
