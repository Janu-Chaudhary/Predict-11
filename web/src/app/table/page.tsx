import { redirect } from "next/navigation";

import { CURRENT_SEASON } from "@/lib/seasons";

/** /table → the current season's table. */
export default function TableIndexPage() {
  redirect(`/table/${CURRENT_SEASON}`);
}
