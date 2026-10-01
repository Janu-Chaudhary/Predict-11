import { redirect } from "next/navigation";

import { CURRENT_SEASON } from "@/components/data/season-select";

/** /table → the current season's table. */
export default function TableIndexPage() {
  redirect(`/table/${CURRENT_SEASON}`);
}
