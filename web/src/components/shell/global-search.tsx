"use client";

import { MapPin, Search, Shield, UserRound } from "lucide-react";
import { useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";

import { StumpsLoader } from "@/components/loaders/stumps-loader";
import { TeamBadge } from "@/components/player/team-badge";
import { Button } from "@/components/ui/button";
import {
  Command,
  CommandDialog,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
  CommandSeparator,
} from "@/components/ui/command";
import { Kbd } from "@/components/ui/kbd";
import { usePlayerSearch } from "@/lib/api/queries";
import { TEAM_CODES, TEAMS } from "@/lib/tokens";

import { ALL_NAV } from "./nav-items";

const matches = (q: string, ...fields: (string | undefined)[]) => {
  const needle = q.trim().toLowerCase();
  if (!needle) return true;
  return fields.some((f) => f?.toLowerCase().includes(needle));
};

function useDebounced<T>(value: T, ms: number) {
  const [v, setV] = useState(value);
  useEffect(() => {
    const t = setTimeout(() => setV(value), ms);
    return () => clearTimeout(t);
  }, [value, ms]);
  return v;
}

/**
 * Global ⌘K search (§3.1): players (API), teams (static), venues (once the endpoint exists)
 * and every nav destination. Replaces all free-text name boxes.
 */
export function GlobalSearch() {
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const debounced = useDebounced(query, 200);
  const search = usePlayerSearch(debounced);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setOpen((o) => !o);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  const go = (href: string) => {
    setOpen(false);
    setQuery("");
    router.push(href);
  };

  const navHits = useMemo(() => ALL_NAV.filter((n) => matches(query, n.label, n.description)), [query]);
  const teamHits = useMemo(
    () => TEAM_CODES.filter((c) => matches(query, c, TEAMS[c].name)).slice(0, query ? 10 : 4),
    [query],
  );

  const term = debounced.trim();
  const searching = term.length >= 2;
  const result = search.data;
  const playerHits = searching && result?.status === "ok" ? result.hits.slice(0, 8) : [];
  const unavailable = searching && result?.status === "unavailable" ? result.reason : null;
  const nothing = navHits.length === 0 && teamHits.length === 0 && playerHits.length === 0;

  return (
    <>
      <Button
        variant="outline"
        onClick={() => setOpen(true)}
        aria-label="Search players, teams and venues"
        aria-keyshortcuts="Meta+K Control+K"
        className="h-9 gap-2 rounded-[10px] border-border bg-surface-1/60 px-2.5 text-muted-foreground max-md:w-9 max-md:px-0 md:w-56 md:justify-start"
      >
        <Search aria-hidden className="size-4" />
        <span className="hidden flex-1 text-left text-sm md:inline">Search</span>
        <Kbd className="hidden md:inline-flex">⌘K</Kbd>
      </Button>
      <CommandDialog
        open={open}
        onOpenChange={(o) => {
          setOpen(o);
          if (!o) setQuery("");
        }}
        title="Search Predict-11"
        description="Search players, teams, venues and pages"
        className="sm:max-w-lg"
      >
        {/* We filter ourselves: player hits arrive ranked from the server. */}
        <Command shouldFilter={false} loop className="bg-transparent">
          <CommandInput value={query} onValueChange={setQuery} placeholder="Search players, teams, venues…" />
          <CommandList className="max-h-[min(60dvh,26rem)]">
            {searching && search.isFetching && (
              <div className="flex items-center gap-2 px-3 py-2 text-xs text-muted-foreground" aria-live="polite">
                <StumpsLoader size={20} label={null} />
                Searching players…
              </div>
            )}
            {nothing && !search.isFetching && (
              <CommandEmpty>
                {unavailable ? unavailable : searching ? `No matches for “${term}”.` : "Type to search."}
              </CommandEmpty>
            )}

            {playerHits.length > 0 && (
              <CommandGroup heading="Players">
                {playerHits.map((p) => (
                  <CommandItem key={p.id} value={`player-${p.id}`} onSelect={() => go(`/players/${encodeURIComponent(p.id)}`)}>
                    <UserRound aria-hidden />
                    <span className="flex-1 truncate">{p.name}</span>
                    {p.role && <span className="text-xs text-muted-foreground">{p.role}</span>}
                    {p.team && <TeamBadge team={p.team} />}
                  </CommandItem>
                ))}
              </CommandGroup>
            )}
            {searching && unavailable && !nothing && (
              <p className="px-3 py-2 text-xs text-muted-foreground">Players: {unavailable}</p>
            )}

            {teamHits.length > 0 && (
              <CommandGroup heading="Teams">
                {teamHits.map((c) => (
                  <CommandItem key={c} value={`team-${c}`} onSelect={() => go(`/teams/${c.toLowerCase()}`)}>
                    <Shield aria-hidden />
                    <span className="flex-1 truncate">{TEAMS[c].name}</span>
                    <TeamBadge team={c} />
                  </CommandItem>
                ))}
              </CommandGroup>
            )}

            {navHits.length > 0 && (
              <>
                <CommandSeparator />
                <CommandGroup heading="Go to">
                  {navHits.map((n) => {
                    const Icon = n.icon;
                    return (
                      <CommandItem key={n.href} value={`nav-${n.href}`} onSelect={() => go(n.href)}>
                        <Icon aria-hidden />
                        <span className="flex-1">{n.label}</span>
                        {n.description && <span className="hidden truncate text-xs text-muted-foreground sm:inline">{n.description}</span>}
                      </CommandItem>
                    );
                  })}
                </CommandGroup>
              </>
            )}
            {matches(query, "venues", "ground", "stadium") && (
              <CommandGroup heading="Venues">
                <CommandItem value="nav-venues-index" onSelect={() => go("/venues")}>
                  <MapPin aria-hidden />
                  <span className="flex-1">Browse all venues</span>
                  <span className="text-xs text-muted-foreground">Venue search arrives with the venues API</span>
                </CommandItem>
              </CommandGroup>
            )}
          </CommandList>
        </Command>
      </CommandDialog>
    </>
  );
}
