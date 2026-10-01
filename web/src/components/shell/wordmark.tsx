import Link from "next/link";

import { cn } from "@/lib/utils";

/** Predict-11 wordmark. The pink→violet gradient lives here and almost nowhere else (§2.2). */
export function Wordmark({ className }: { className?: string }) {
  return (
    <Link
      href="/"
      aria-label="Predict-11 home"
      className={cn("inline-flex items-center gap-2 rounded-md outline-none focus-visible:ring-2 focus-visible:ring-ring", className)}
    >
      <span aria-hidden className="flex size-7 items-center justify-center rounded-full bg-primary text-primary-foreground">
        <span className="font-condensed text-[13px] leading-none font-bold">11</span>
      </span>
      <span className="text-brand-gradient font-display text-lg leading-none font-bold tracking-tight [font-stretch:87.5%]">
        Predict-11
      </span>
    </Link>
  );
}
