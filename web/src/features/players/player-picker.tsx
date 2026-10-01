"use client";

import { Search, X } from "lucide-react";
import { useEffect, useId, useRef, useState } from "react";

import { StumpsLoader } from "@/components/loaders/stumps-loader";
import { PlayerAvatar } from "@/components/player/player-avatar";
import { TeamBadge } from "@/components/player/team-badge";
import { cn } from "@/lib/utils";

import { displayName, photoOf, seasonSpan, teamCode } from "./format";
import { usePlayerSearchHits } from "./queries";
import type { SearchHit } from "./types";

export function useDebounced<T>(value: T, ms = 200): T {
  const [v, setV] = useState(value);
  useEffect(() => {
    const t = setTimeout(() => setV(value), ms);
    return () => clearTimeout(t);
  }, [value, ms]);
  return v;
}

/** `name` is the display name (full name when the API has one). */
export type PickedPlayer = { id: string; name: string; team?: string | null; image?: string | null };

/**
 * Player autocomplete (ARIA 1.2 combobox + listbox). Searches names *and aliases* via
 * /players/search, debounced 200 ms, so nobody has to type exact Cricsheet names.
 * Only players with IPL matches are offered.
 */
export function PlayerPicker({
  label,
  value,
  onChange,
  placeholder = "Search a player…",
  hideLabel = false,
  exclude = [],
  autoFocus = false,
  className,
}: {
  label: string;
  value: PickedPlayer | null;
  onChange: (p: PickedPlayer | null) => void;
  placeholder?: string;
  hideLabel?: boolean;
  /** ids that can't be picked (already chosen elsewhere). */
  exclude?: string[];
  autoFocus?: boolean;
  className?: string;
}) {
  const uid = useId();
  const inputId = `${uid}-input`;
  const listId = `${uid}-list`;
  const [editing, setEditing] = useState(value === null);
  const [query, setQuery] = useState("");
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);
  const debounced = useDebounced(query, 200);
  const search = usePlayerSearchHits(debounced, 12);

  const term = debounced.trim();
  const hits: SearchHit[] = term.length >= 2 ? (search.data?.results ?? []).filter((h) => h.matches > 0 && !exclude.includes(h.id)).slice(0, 8) : [];
  const showList = open && query.trim().length >= 2;
  const activeIdx = Math.min(active, Math.max(hits.length - 1, 0));

  const pick = (h: SearchHit) => {
    onChange({ id: h.id, name: displayName(h), team: h.team, image: photoOf(h) });
    setQuery("");
    setOpen(false);
    setEditing(false);
  };

  const startEdit = () => {
    setEditing(true);
    setQuery("");
    requestAnimationFrame(() => inputRef.current?.focus());
  };

  const status = (() => {
    if (query.trim().length < 2) return null;
    if (search.isError) return "Search is unavailable right now.";
    if (search.isFetching && hits.length === 0) return "Searching…";
    if (!search.isFetching && term && hits.length === 0) return `No IPL players match “${term}”.`;
    return null;
  })();

  return (
    <div className={cn("relative min-w-0", className)}>
      <label htmlFor={inputId} className={cn("text-overline mb-1.5 block text-muted-foreground", hideLabel && "sr-only")}>
        {label}
      </label>
      {!(editing || value === null) && value ? (
        <div className="flex h-11 items-center gap-2 rounded-[10px] border border-border bg-card pr-1 pl-2">
          <PlayerAvatar name={value.name} src={value.image} team={teamCode(value.team) ?? undefined} size="xs" />
          <span className="min-w-0 flex-1 truncate text-sm font-semibold">{value.name}</span>
          {value.team && <TeamBadge team={teamCode(value.team) ?? ""} />}
          <button
            type="button"
            onClick={startEdit}
            className="inline-flex h-9 items-center rounded-lg px-2.5 text-xs font-medium text-brand outline-none hover:bg-surface-2 focus-visible:ring-2 focus-visible:ring-ring"
            aria-label={`Change ${label.toLowerCase()} (currently ${value.name})`}
            id={inputId}
          >
            Change
          </button>
        </div>
      ) : (
        <div className="relative">
          <Search aria-hidden className="pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2 text-muted-foreground" />
          <input
            ref={inputRef}
            id={inputId}
            type="text"
            role="combobox"
            autoComplete="off"
            spellCheck={false}
            autoFocus={autoFocus}
            aria-expanded={showList}
            aria-controls={listId}
            aria-autocomplete="list"
            aria-activedescendant={showList && hits[activeIdx] ? `${listId}-${activeIdx}` : undefined}
            placeholder={placeholder}
            value={query}
            onChange={(e) => {
              setQuery(e.target.value);
              setOpen(true);
              setActive(0);
            }}
            onFocus={() => setOpen(true)}
            onBlur={() => setTimeout(() => setOpen(false), 120)}
            onKeyDown={(e) => {
              if (e.key === "ArrowDown") {
                e.preventDefault();
                setOpen(true);
                setActive((a) => (hits.length ? (a + 1) % hits.length : 0));
              } else if (e.key === "ArrowUp") {
                e.preventDefault();
                setActive((a) => (hits.length ? (a - 1 + hits.length) % hits.length : 0));
              } else if (e.key === "Enter") {
                if (showList && hits[activeIdx]) {
                  e.preventDefault();
                  pick(hits[activeIdx]);
                }
              } else if (e.key === "Escape") {
                if (showList) setOpen(false);
                else if (value) setEditing(false);
              }
            }}
            className="h-11 w-full min-w-0 rounded-[10px] border border-input bg-card pr-9 pl-9 text-base outline-none placeholder:text-muted-foreground focus-visible:border-ring focus-visible:ring-2 focus-visible:ring-ring/60 md:text-sm"
          />
          {search.isFetching && query.trim().length >= 2 ? (
            <span className="absolute top-1/2 right-2.5 -translate-y-1/2">
              <StumpsLoader size={20} label={null} />
            </span>
          ) : value ? (
            <button
              type="button"
              aria-label={`Keep ${value.name}`}
              onClick={() => setEditing(false)}
              className="absolute top-1/2 right-1 inline-flex size-9 -translate-y-1/2 items-center justify-center rounded-lg text-muted-foreground hover:text-foreground focus-visible:ring-2 focus-visible:ring-ring"
            >
              <X aria-hidden className="size-4" />
            </button>
          ) : null}
        </div>
      )}
      <ul
        id={listId}
        role="listbox"
        aria-label={`${label} suggestions`}
        hidden={!showList || hits.length === 0}
        className="absolute inset-x-0 top-full z-40 mt-1 max-h-80 overflow-auto rounded-xl border border-border bg-popover p-1 shadow-lg"
      >
        {hits.map((h, i) => {
          const code = teamCode(h.team);
          const shown = displayName(h);
          const viaAlias = h.matched && h.matched !== h.name && h.matched !== shown;
          return (
            <li
              key={h.id}
              id={`${listId}-${i}`}
              role="option"
              aria-selected={i === activeIdx}
              onMouseDown={(e) => e.preventDefault()}
              onMouseEnter={() => setActive(i)}
              onClick={() => pick(h)}
              className={cn("flex min-h-11 cursor-pointer items-center gap-2.5 rounded-lg px-2 py-1.5", i === activeIdx && "bg-surface-2")}
            >
              <PlayerAvatar name={shown} src={photoOf(h)} team={code ?? undefined} size="sm" />
              <span className="min-w-0 flex-1">
                <span className="block truncate text-sm font-medium">{shown}</span>
                <span className="num block truncate text-xs text-muted-foreground">
                  {shown !== h.name && <>{h.name} · </>}
                  {viaAlias && <>“{h.matched}” · </>}
                  {h.first_season ? seasonSpan([h.first_season, h.last_season ?? h.first_season]) : ""} · {h.matches} matches
                </span>
              </span>
              {code && <TeamBadge team={code} />}
            </li>
          );
        })}
      </ul>
      <p aria-live="polite" className={cn("text-xs text-muted-foreground", status && showList ? "mt-1.5" : "sr-only")}>
        {showList ? (status ?? (hits.length ? `${hits.length} players found` : "")) : ""}
      </p>
    </div>
  );
}
