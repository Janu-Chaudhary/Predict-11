import { ROLE_THEME, type Role } from "@/lib/tokens";
import { cn } from "@/lib/utils";

export function RoleChip({ role, className }: { role: Role; className?: string }) {
  const r = ROLE_THEME[role];
  return (
    <span
      title={r.label}
      className={cn("inline-flex h-5 items-center rounded px-1.5 text-[10px] font-semibold ring-1 ring-inset", r.chip, className)}
    >
      <span aria-hidden>{role}</span>
      <span className="sr-only">{r.label}</span>
    </span>
  );
}
