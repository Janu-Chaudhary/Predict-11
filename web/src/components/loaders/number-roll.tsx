"use client";

import { digitOffset, rollTokens } from "@/lib/digits";
import { cn } from "@/lib/utils";

const DIGITS = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9];

/**
 * Scoreboard digit roll (§7.2 #4) — not a loader. When `value` changes each digit column
 * slides to its new glyph in 300 ms. Inherits font size; tabular numerals keep widths fixed.
 * Reduced motion → instant swap. Screen readers get the whole formatted value once.
 */
export function NumberRoll({
  value,
  format = (n) => String(n),
  label,
  className,
}: {
  value: number;
  format?: (n: number) => string;
  /** Accessible label; defaults to the formatted value. */
  label?: string;
  className?: string;
}) {
  const text = format(value);
  const tokens = rollTokens(text);
  return (
    <span
      role="img"
      aria-label={label ?? text}
      data-value={text}
      className={cn("num inline-flex leading-[1.15]", className)}
    >
      {tokens.map((t) =>
        t.kind === "digit" ? (
          <span key={t.key} aria-hidden className="relative inline-block h-[1.15em] overflow-hidden">
            <span
              data-digit={t.value}
              className="block transition-transform duration-300 ease-emphasized motion-reduce:transition-none"
              style={{ transform: digitOffset(t.value) }}
            >
              {DIGITS.map((d) => (
                <span key={d} className="block h-[1.15em]">
                  {d}
                </span>
              ))}
            </span>
          </span>
        ) : (
          <span key={t.key} aria-hidden>
            {t.value}
          </span>
        ),
      )}
    </span>
  );
}
