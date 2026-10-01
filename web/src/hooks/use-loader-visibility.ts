"use client";

import { useEffect, useRef, useState } from "react";

export type LoaderTiming = {
  /** Wait this long before showing the loader at all (avoids flashes). §7.2: 800 ms for the app loader. */
  showDelay?: number;
  /** Once shown, keep it on screen at least this long (no blink). §7.2: 600 ms. */
  minVisible?: number;
  /** After this long, flag the wait as slow ("Taking longer than usual · Retry"). §7.2: 8 s. */
  slowAfter?: number;
};

export const APP_LOADER_TIMING = { showDelay: 800, minVisible: 600, slowAfter: 8000 } as const satisfies Required<LoaderTiming>;
export const INLINE_LOADER_TIMING = { showDelay: 300, minVisible: 400, slowAfter: 8000 } as const satisfies Required<LoaderTiming>;

/**
 * Turns a raw `pending` flag into loader visibility that follows the §7.2 timing rules:
 * nothing for short waits, then a loader that never blinks, plus a "slow" flag.
 * All state changes happen in timer callbacks, so it is safe under StrictMode.
 */
export function useLoaderVisibility(pending: boolean, timing: LoaderTiming = APP_LOADER_TIMING) {
  const { showDelay = APP_LOADER_TIMING.showDelay, minVisible = APP_LOADER_TIMING.minVisible, slowAfter = APP_LOADER_TIMING.slowAfter } = timing;
  const [visible, setVisible] = useState(false);
  const [slow, setSlow] = useState(false);
  const shownAt = useRef<number | null>(null);

  useEffect(() => {
    if (pending) {
      const show = setTimeout(() => {
        shownAt.current = Date.now();
        setVisible(true);
      }, showDelay);
      const slowTimer = setTimeout(() => setSlow(true), slowAfter);
      return () => {
        clearTimeout(show);
        clearTimeout(slowTimer);
      };
    }
    // Not pending: hide, but only after the loader has been visible for `minVisible`.
    const elapsed = shownAt.current === null ? Infinity : Date.now() - shownAt.current;
    const wait = Math.max(0, minVisible - elapsed);
    const hide = setTimeout(() => {
      shownAt.current = null;
      setVisible(false);
      setSlow(false);
    }, wait);
    return () => clearTimeout(hide);
  }, [pending, showDelay, minVisible, slowAfter]);

  return { visible, slow };
}
