"use client";

import { useState } from "react";

import { CURRENT_SEASON, SeasonSelect } from "@/components/data/season-select";

export function MatchesSeasonSelect() {
  const [season, setSeason] = useState(CURRENT_SEASON);
  return <SeasonSelect value={season} onValueChange={setSeason} />;
}
