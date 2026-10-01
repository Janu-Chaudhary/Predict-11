/**
 * The records/venue endpoints return full franchise names ("Mumbai Indians"); TeamBadge wants a
 * code. Local map (feature-scoped) until the API ships team codes. Unknown names fall back to
 * an uppercase initialism, which TeamBadge renders in neutral colours.
 */
const BY_NAME: Record<string, string> = {
  "chennai super kings": "CSK",
  "mumbai indians": "MI",
  "royal challengers bengaluru": "RCB",
  "royal challengers bangalore": "RCB",
  "kolkata knight riders": "KKR",
  "delhi capitals": "DC",
  "delhi daredevils": "DC",
  "punjab kings": "PBKS",
  "kings xi punjab": "PBKS",
  "rajasthan royals": "RR",
  "sunrisers hyderabad": "SRH",
  "gujarat titans": "GT",
  "lucknow super giants": "LSG",
  "deccan chargers": "DCG",
  "kochi tuskers kerala": "KTK",
  "pune warriors": "PWI",
  "pune warriors india": "PWI",
  "rising pune supergiant": "RPS",
  "rising pune supergiants": "RPS",
  "gujarat lions": "GL",
};

export function teamCode(name: string | null | undefined): string | null {
  if (!name) return null;
  const hit = BY_NAME[name.trim().toLowerCase()];
  if (hit) return hit;
  return name
    .split(/\s+/)
    .map((w) => w[0] ?? "")
    .join("")
    .toUpperCase()
    .slice(0, 4);
}
