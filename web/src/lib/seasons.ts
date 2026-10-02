/**
 * IPL seasons with data, newest first. Plain module (no "use client") so server components can
 * read these values; importing them from a client module hands the server a reference stub.
 */
export const SEASONS = Array.from({ length: 2026 - 2008 + 1 }, (_, i) => 2026 - i);
export const CURRENT_SEASON = SEASONS[0];
