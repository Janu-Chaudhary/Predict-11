import { HeaderSkeleton, RowsSkeleton } from "@/components/loaders/page-skeletons";

export default function Loading() {
  return (
    <div role="status" aria-busy="true" aria-label="Loading fantasy">
      <HeaderSkeleton withActions />
      <RowsSkeleton rows={10} />
    </div>
  );
}
