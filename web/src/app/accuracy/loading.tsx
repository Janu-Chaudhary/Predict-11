import { ChartSkeleton, HeaderSkeleton, TilesSkeleton } from "@/components/loaders/page-skeletons";

export default function Loading() {
  return (
    <div role="status" aria-busy="true" aria-label="Loading predictions">
      <HeaderSkeleton />
      <TilesSkeleton />
      <ChartSkeleton className="mt-4" />
    </div>
  );
}
