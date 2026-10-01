import { AllRounderIcon, BallIcon, BatIcon, GlovesIcon } from "@/components/icons/cricket";
import { ROLE_THEME, type Role } from "@/lib/tokens";
import { cn } from "@/lib/utils";

const ICON = { WK: GlovesIcon, BAT: BatIcon, AR: AllRounderIcon, BOWL: BallIcon } as const;

/** Role chip: icon + text code (never colour alone). The four role hues are reserved for roles. */
export function RoleChip({ role, showIcon = true, className }: { role: Role; showIcon?: boolean; className?: string }) {
  const r = ROLE_THEME[role];
  const Icon = ICON[role];
  return (
    <span
      title={r.label}
      className={cn(
        "inline-flex h-6 items-center gap-1 rounded-full px-2 text-[11px] leading-none font-semibold ring-1 ring-inset",
        r.chip,
        className,
      )}
    >
      {showIcon && <Icon size={12} strokeWidth={2} />}
      <span aria-hidden>{role}</span>
      <span className="sr-only">{r.label}</span>
    </span>
  );
}
