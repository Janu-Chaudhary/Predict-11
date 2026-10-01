import { cn } from "@/lib/utils";

/** C = gold roundel; VC = roundel with the brand-gradient ring (§2.2). */
export function CaptainRoundel({ kind, className }: { kind: "C" | "VC"; className?: string }) {
  const label = kind === "C" ? "Captain" : "Vice-captain";
  if (kind === "C") {
    return (
      <span
        role="img"
        aria-label={label}
        title={label}
        className={cn("font-condensed inline-flex size-5 items-center justify-center rounded-full bg-primary text-[11px] leading-none font-bold text-primary-foreground", className)}
      >
        C
      </span>
    );
  }
  return (
    <span
      role="img"
      aria-label={label}
      title={label}
      className={cn("bg-brand-gradient inline-flex size-5 items-center justify-center rounded-full p-[1.5px]", className)}
    >
      <span className="flex size-full items-center justify-center rounded-full bg-card font-condensed text-[11px] leading-none font-bold text-foreground">VC</span>
    </span>
  );
}
