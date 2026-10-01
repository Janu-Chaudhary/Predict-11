"use client";

import { RotateCcw } from "lucide-react";

import { Button } from "@/components/ui/button";
import { APP_LOADER_TIMING, useLoaderVisibility, type LoaderTiming } from "@/hooks/use-loader-visibility";
import { cn } from "@/lib/utils";

import { SeamSpin } from "./seam-spin";

/**
 * Client-controlled app loader for cold starts / whole-route waits with no layout yet.
 * Appears only after 800 ms, then stays ≥ 600 ms and cross-fades out over 200 ms.
 * After 8 s it adds "Taking longer than usual" and an optional Retry.
 */
export function AppLoader({
  pending,
  label,
  onRetry,
  timing = APP_LOADER_TIMING,
  className,
}: {
  pending: boolean;
  label?: string;
  onRetry?: () => void;
  timing?: LoaderTiming;
  className?: string;
}) {
  const { visible, slow } = useLoaderVisibility(pending, timing);
  return (
    <div
      aria-hidden={!visible}
      data-visible={visible}
      className={cn(
        "grid min-h-[40dvh] place-items-center transition-opacity duration-200 ease-emphasized motion-reduce:duration-[120ms]",
        visible ? "opacity-100" : "pointer-events-none opacity-0",
        className,
      )}
    >
      {visible && (
        <div className="grid justify-items-center gap-3">
          <SeamSpin label={label} />
          {slow && (
            <div className="grid justify-items-center gap-2 text-xs text-muted-foreground">
              <span>Taking longer than usual</span>
              {onRetry && (
                <Button size="sm" variant="outline" onClick={onRetry}>
                  <RotateCcw aria-hidden />
                  Retry
                </Button>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

/**
 * Server-renderable variant for `loading.tsx`: the 800 ms delay is a CSS animation-delay,
 * so it works before hydration. (The 600 ms minimum cannot be enforced once React swaps the
 * Suspense fallback out — use `AppLoader` where the pending flag is known.)
 */
export function AppLoaderFallback({ label }: { label?: string }) {
  return (
    <div className="app-loader-delayed grid min-h-[50dvh] place-items-center">
      <SeamSpin label={label} />
    </div>
  );
}
