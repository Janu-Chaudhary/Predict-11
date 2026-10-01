import { Skeleton } from "@/components/ui/skeleton";

/** Mirrors HomeView's grid (hero box, card, bento) so swapping in content causes no shift. */
export function HomeSkeleton() {
  return (
    <div role="status" aria-busy="true" aria-label="Loading home">
      <div className="grid items-center gap-5 lg:grid-cols-[1.25fr_1fr] lg:gap-8">
        <Skeleton className="aspect-[358/300] w-full rounded-2xl sm:aspect-[16/10]" />
        <div className="grid gap-4 rounded-2xl border border-border bg-card p-5">
          <Skeleton className="h-3 w-48" />
          <Skeleton className="h-8 w-64" />
          <Skeleton className="h-16 w-full rounded-[10px]" />
          <Skeleton className="h-24 w-full" />
          <div className="flex gap-2">
            <Skeleton className="h-11 flex-1 rounded-[10px]" />
            <Skeleton className="h-11 flex-1 rounded-[10px]" />
          </div>
        </div>
      </div>
      <div className="mt-8 grid grid-cols-2 gap-3 md:gap-4 lg:mt-10 lg:grid-cols-4">
        <Skeleton className="col-span-2 h-[132px] rounded-xl lg:row-span-2 lg:h-auto" />
        {Array.from({ length: 4 }, (_, i) => (
          <Skeleton key={i} className="h-[132px] rounded-xl" />
        ))}
      </div>
    </div>
  );
}
