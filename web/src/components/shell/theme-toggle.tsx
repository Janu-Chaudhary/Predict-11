"use client";

import { Monitor, Moon, Sun } from "lucide-react";
import { useTheme } from "next-themes";
import { useSyncExternalStore } from "react";

import { Button } from "@/components/ui/button";

const ORDER = ["dark", "light", "system"] as const;
type Mode = (typeof ORDER)[number];
const ICON = { system: Monitor, light: Sun, dark: Moon };

const subscribe = () => () => {};

/** Cycles dark → light → system. Dark is the default theme. */
export function ThemeToggle() {
  const { theme, setTheme } = useTheme();
  // Avoid hydration mismatch: the stored theme is only known on the client.
  const mounted = useSyncExternalStore(subscribe, () => true, () => false);
  const current: Mode = mounted && ORDER.includes(theme as Mode) ? (theme as Mode) : "dark";
  const next = ORDER[(ORDER.indexOf(current) + 1) % ORDER.length];
  const Icon = ICON[current];
  return (
    <Button
      variant="ghost"
      size="icon"
      className="size-9 rounded-[10px]"
      aria-label={`Theme: ${current}. Switch to ${next}`}
      onClick={() => setTheme(next)}
    >
      <Icon aria-hidden className="size-[18px]" strokeWidth={1.75} />
    </Button>
  );
}
