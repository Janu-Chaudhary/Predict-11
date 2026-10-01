import { FreshnessBadge } from "./freshness-badge";
import { GlobalSearch } from "./global-search";
import { ThemeToggle } from "./theme-toggle";
import { Wordmark } from "./wordmark";

/** 56 px glass top bar: wordmark · freshness · search (⌘K) · theme. */
export function TopBar() {
  return (
    <header className="glass sticky top-0 z-40 h-14 border-b border-border pt-[env(safe-area-inset-top)]">
      <div className="flex h-full items-center justify-between gap-2 px-4 lg:px-5">
        <Wordmark />
        <div className="flex items-center gap-1.5 sm:gap-2">
          <FreshnessBadge />
          <GlobalSearch />
          <ThemeToggle />
        </div>
      </div>
    </header>
  );
}
