import { ChartSkeleton, HeaderSkeleton, TabsSkeleton, TilesSkeleton } from "@/components/loaders/page-skeletons";

export default function Loading() {
  return (
    <div role="status" aria-busy="true" aria-label="Loading the Model Lab">
      <HeaderSkeleton withActions />
      <TabsSkeleton tabs={8} />
      <TilesSkeleton count={4} />
      <ChartSkeleton className="mt-4" />
    </div>
  );
}
