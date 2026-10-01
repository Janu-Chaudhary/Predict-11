/** Tokeniser for the scoreboard digit roll (§7.2 #4). */

export type RollToken =
  | { kind: "digit"; value: number; key: string }
  | { kind: "char"; value: string; key: string };

/**
 * Split a formatted number ("1,284.5", "-0.41", "+12") into digit columns and static characters.
 * Keys count from the right so units stay in the same column when the length changes
 * (98 → 102 rolls the last two digits rather than re-mounting everything).
 */
export function rollTokens(formatted: string): RollToken[] {
  const chars = [...formatted];
  return chars.map((ch, i) => {
    const fromRight = chars.length - 1 - i;
    if (ch >= "0" && ch <= "9") return { kind: "digit", value: Number(ch), key: `d${fromRight}` };
    return { kind: "char", value: ch, key: `c${fromRight}-${ch}` };
  });
}

/** translateY for a digit column (10 stacked glyphs): −value × 10% of the column's own height. */
export function digitOffset(value: number): string {
  return `translateY(-${value * 10}%)`;
}
