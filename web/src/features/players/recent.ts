"use client";

import { useSyncExternalStore } from "react";

import type { PickedPlayer } from "./player-picker";

/** Recently viewed players: a per-browser convenience only (may be empty or unavailable). */
const KEY = "p11:recent-players";
const MAX = 8;
const EMPTY: PickedPlayer[] = [];
const listeners = new Set<() => void>();
let cache: { raw: string | null; list: PickedPlayer[] } = { raw: null, list: EMPTY };

function read(): PickedPlayer[] {
  let raw: string | null = null;
  try {
    raw = window.localStorage.getItem(KEY);
  } catch {
    return EMPTY;
  }
  if (raw === cache.raw) return cache.list;
  let list: PickedPlayer[] = EMPTY;
  try {
    const parsed: unknown = raw ? JSON.parse(raw) : [];
    if (Array.isArray(parsed)) list = parsed.filter((p): p is PickedPlayer => !!p && typeof p.id === "string" && typeof p.name === "string").slice(0, MAX);
  } catch {
    list = EMPTY;
  }
  cache = { raw, list };
  return list;
}

export function rememberPlayer(p: PickedPlayer) {
  try {
    const next = [p, ...read().filter((x) => x.id !== p.id)].slice(0, MAX);
    window.localStorage.setItem(KEY, JSON.stringify(next));
    listeners.forEach((l) => l());
  } catch {
    /* storage blocked: nothing to remember */
  }
}

export function useRecentPlayers(): PickedPlayer[] {
  return useSyncExternalStore(
    (cb) => {
      listeners.add(cb);
      return () => listeners.delete(cb);
    },
    read,
    () => EMPTY,
  );
}
