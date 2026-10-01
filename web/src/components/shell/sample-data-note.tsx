import { FlaskConical } from "lucide-react";

import { cn } from "@/lib/utils";

/** Marks a layout preview rendered with sample props until the real endpoint lands. */
export function SampleDataNote({ children, className }: { children?: React.ReactNode; className?: string }) {
  return (
    <p
      className={cn(
        "flex items-start gap-2 rounded-lg border border-warning/30 bg-warning/8 px-3 py-2 text-xs text-foreground",
        className,
      )}
    >
      <FlaskConical aria-hidden className="mt-px size-3.5 shrink-0 text-warning" />
      <span>
        <span className="font-semibold">Sample data.</span>{" "}
        {children ?? "This is a layout preview; the numbers are not real and will be replaced by the API."}
      </span>
    </p>
  );
}
