import { HeaderSkeleton } from "@/components/loaders/page-skeletons";
import { Skeleton } from "@/components/ui/skeleton";

export default function Loading() {
  return (
    <div role="status" aria-busy="true" aria-label="Loading builder">
      <HeaderSkeleton />
      <Skeleton className="mb-4 h-12 w-full rounded-xl" />
      <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_20rem]">
        <Skeleton className="h-[520px] rounded-2xl" />
        <Skeleton className="h-56 rounded-xl" />
      </div>
    </div>
  );
}
