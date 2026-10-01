import { TabLinks } from "@/components/shell/tab-links";

const PATHS: Record<string, string> = {
  records: "/records",
  milestones: "/records/milestones",
  streaks: "/records/streaks",
};

/** Sibling navigation between the records pages (all-time records, milestones watch, streaks). */
export function RecordsSubnav({ active, season }: { active: "milestones" | "streaks"; season: number | null }) {
  return (
    <TabLinks
      label="Records sections"
      active={active}
      tabs={[
        { key: "records", label: "Records" },
        { key: "milestones", label: "Milestones watch" },
        { key: "streaks", label: "Streaks" },
      ]}
      hrefFor={(k) => (season ? `${PATHS[k]}?season=${season}` : PATHS[k])}
    />
  );
}
