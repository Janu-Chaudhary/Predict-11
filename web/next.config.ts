import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  images: {
    // Player photos come from the official IPL hosts (originals ~1.1 MB PNG): let Next resize,
    // re-encode and cache them. Team logos are local under /public/teams.
    remotePatterns: [
      { protocol: "https", hostname: "documents.iplt20.com", pathname: "/**" },
      { protocol: "https", hostname: "www.iplt20.com", pathname: "/api/team-assets/**" },
    ],
    formats: ["image/avif", "image/webp"],
    qualities: [75],
    // Small avatar/badge widths so 1x/2x srcsets stay tiny.
    imageSizes: [16, 24, 32, 40, 48, 56, 64, 96, 128, 160, 256],
    minimumCacheTTL: 60 * 60 * 24 * 30,
    maximumResponseBody: 8_000_000,
  },
  // Old scaffold routes → v2 IA (§3.2: Fixtures → Matches, Review → match tab `review`).
  async redirects() {
    return [
      { source: "/builder", destination: "/build", permanent: false },
      { source: "/review", destination: "/matches", permanent: false },
      { source: "/settings", destination: "/more", permanent: false },
    ];
  },
};

export default nextConfig;
