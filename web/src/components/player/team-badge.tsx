import { TEAMS, type TeamCode } from "@/lib/tokens";
import { cn } from "@/lib/utils";

export function TeamBadge({ team, className }: { team: TeamCode; className?: string }) {
  const t = TEAMS[team];
  return (
    <span
      title={t.name}
      aria-label={t.name}
      className={cn(
        "inline-flex h-5 min-w-9 items-center justify-center rounded px-1.5 text-[10px] leading-none font-bold tracking-wide",
        className,
      )}
      style={{ backgroundColor: t.primary, color: t.onPrimary, boxShadow: `inset 0 -2px 0 ${t.secondary}` }}
    >
      {t.short}
    </span>
  );
}
