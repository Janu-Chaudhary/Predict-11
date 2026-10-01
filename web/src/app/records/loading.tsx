import { HeaderSkeleton, TableSkeleton } from "@/components/loaders/page-skeletons";
import { Skeleton } from "@/components/ui/skeleton";

export default function Loading() {
  return (
    <div role="status" aria-busy="true" aria-label="Loading records">
      <HeaderSkeleton />
      <div className="mb-4 flex gap-2">
        <Skeleton className="h-10 w-36 rounded-[10px]" />
        <Skeleton className="h-10 w-36 rounded-[10px]" />
      </div>
      <div className="grid gap-4 lg:grid-cols-2">
        {Array.from({ length: 4 }, (_, i) => (
          <TableSkeleton key={i} rows={10} cols={5} />
        ))}
      </div>
    </div>
  );
}
