"use client";

import { Monitor, Moon, Sun } from "lucide-react";
import { useTheme } from "next-themes";
import { useSyncExternalStore } from "react";

import { Button } from "@/components/ui/button";

const ORDER = ["system", "light", "dark"] as const;
const ICON = { system: Monitor, light: Sun, dark: Moon };

const subscribe = () => () => {};

/** Cycles system → light → dark. */
export function ThemeToggle() {
  const { theme, setTheme } = useTheme();
  // Avoid hydration mismatch: theme is only known on the client.
  const mounted = useSyncExternalStore(subscribe, () => true, () => false);
  const current = (mounted && ORDER.includes(theme as (typeof ORDER)[number]) ? theme : "system") as (typeof ORDER)[number];
  const next = ORDER[(ORDER.indexOf(current) + 1) % ORDER.length];
  const Icon = ICON[current];
  return (
    <Button
      variant="ghost"
      size="icon"
      aria-label={`Theme: ${current}. Switch to ${next}`}
      onClick={() => setTheme(next)}
    >
      <Icon aria-hidden />
    </Button>
  );
}
