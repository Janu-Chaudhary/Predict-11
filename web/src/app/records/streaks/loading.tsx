import { HeaderSkeleton } from "@/components/loaders/page-skeletons";
import { StreaksSkeleton } from "@/features/milestones/streaks-board";

export default function Loading() {
  return (
    <>
      <HeaderSkeleton withActions />
      <StreaksSkeleton />
    </>
  );
}
