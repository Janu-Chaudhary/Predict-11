import Link from "next/link";

import { FreshnessBadge } from "./freshness-badge";
import { ThemeToggle } from "./theme-toggle";

export function TopBar() {
  return (
    <header className="sticky top-0 z-40 h-14 border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/80">
      <div className="flex h-full items-center justify-between gap-3 px-4">
        <Link href="/" className="flex items-center gap-2 rounded-md font-semibold tracking-tight outline-none focus-visible:ring-3 focus-visible:ring-ring/50">
          <span aria-hidden className="flex size-7 items-center justify-center rounded-full bg-pitch text-[11px] font-bold text-white">
            11
          </span>
          Predict-11
        </Link>
        <div className="flex items-center gap-1.5">
          <FreshnessBadge />
          <ThemeToggle />
        </div>
      </div>
    </header>
  );
}
