"use client";

import { useTheme } from "next-themes";
import { useSyncExternalStore } from "react";

import type { ThemeName } from "@/lib/tokens";

const noop = () => () => {};

/** "dark" | "light" after mount; "dark" (the default theme) during SSR/hydration. */
export function useResolvedTheme(): ThemeName {
  const { resolvedTheme } = useTheme();
  const mounted = useSyncExternalStore(noop, () => true, () => false);
  return mounted && resolvedTheme === "light" ? "light" : "dark";
}
