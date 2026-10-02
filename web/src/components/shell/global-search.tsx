"use client";

import { MapPin, Search, Shield, UserRound } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";

import { StumpsLoader } from "@/components/loaders/stumps-loader";
import { PlayerAvatar } from "@/components/player/player-avatar";
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
import { teamCode } from "@/features/players/format";
import { fetchVenues, VENUE_STALE_MS, venueKeys } from "@/features/venues/api";
import { usePlayerSearch, usePopularPlayers } from "@/lib/api/queries";
import type { PlayerHit } from "@/lib/api/search";
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

function PlayerItem({ p, onSelect }: { p: PlayerHit; onSelect: () => void }) {
  const team = teamCode(p.team) ?? undefined;
  return (
    <CommandItem value={`player-${p.id}`} onSelect={onSelect}>
      {p.imageUrl ? <PlayerAvatar name={p.name} src={p.imageUrl} team={team} size="xs" /> : <UserRound aria-hidden />}
      <span className="flex-1 truncate">{p.name}</span>
      {p.role && <span className="text-xs text-muted-foreground">{p.role}</span>}
      {team && <TeamBadge team={team} />}
    </CommandItem>
  );
}

/**
 * Global ⌘K search (§3.1): players (API; popular players while empty), teams (static), venues
 * (the /venues list, filtered here) and every nav destination. Replaces all free-text name boxes.
 */
export function GlobalSearch() {
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const debounced = useDebounced(query, 200);
  const search = usePlayerSearch(debounced);
  const popular = usePopularPlayers(open);
  const venues = useQuery({ queryKey: venueKeys.list, queryFn: ({ signal }) => fetchVenues(signal), staleTime: VENUE_STALE_MS, enabled: open, retry: false });

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
  const suggested = !query.trim() ? (popular.data ?? []) : [];
  const venueHits = useMemo(() => {
    const q = debounced.trim();
    if (q.length < 2) return [];
    return (venues.data?.venues ?? [])
      .filter((v) => matches(q, v.name, v.city ?? undefined))
      .sort((a, b) => b.matches - a.matches)
      .slice(0, 5);
  }, [debounced, venues.data]);
  const nothing = navHits.length === 0 && teamHits.length === 0 && playerHits.length === 0 && venueHits.length === 0;

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
                  <PlayerItem key={p.id} p={p} onSelect={() => go(`/players/${encodeURIComponent(p.id)}`)} />
                ))}
              </CommandGroup>
            )}
            {suggested.length > 0 && (
              <CommandGroup heading="Popular players">
                {suggested.map((p) => (
                  <PlayerItem key={p.id} p={p} onSelect={() => go(`/players/${encodeURIComponent(p.id)}`)} />
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
            {venueHits.length > 0 && (
              <CommandGroup heading="Venues">
                {venueHits.map((v) => (
                  <CommandItem key={v.id} value={`venue-${v.id}`} onSelect={() => go(`/venues/${v.id}`)}>
                    <MapPin aria-hidden />
                    <span className="flex-1 truncate">{v.name}</span>
                    {v.city && <span className="text-xs text-muted-foreground">{v.city}</span>}
                  </CommandItem>
                ))}
              </CommandGroup>
            )}
            {venueHits.length === 0 && matches(query, "venues", "ground", "stadium") && (
              <CommandGroup heading="Venues">
                <CommandItem value="nav-venues-index" onSelect={() => go("/venues")}>
                  <MapPin aria-hidden />
                  <span className="flex-1">Browse all venues</span>
                </CommandItem>
              </CommandGroup>
            )}
          </CommandList>
        </Command>
      </CommandDialog>
    </>
  );
}
