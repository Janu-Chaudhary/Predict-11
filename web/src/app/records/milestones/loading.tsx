import { HeaderSkeleton } from "@/components/loaders/page-skeletons";
import { MilestonesSkeleton } from "@/features/milestones/milestones-watch";

export default function Loading() {
  return (
    <>
      <HeaderSkeleton withActions />
      <MilestonesSkeleton />
    </>
  );
}
