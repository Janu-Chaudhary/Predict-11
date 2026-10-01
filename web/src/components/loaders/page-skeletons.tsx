import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";

/*
 * Route skeletons (§7.2 #3). Each mirrors the grid, row heights and badge sizes of the page
 * it stands in for, so swapping in real content causes no layout shift.
 */

function Busy({ label, children, className }: { label: string; children: React.ReactNode; className?: string }) {
  return (
    <div role="status" aria-busy="true" aria-label={label} className={className}>
      {children}
    </div>
  );
}

export function HeaderSkeleton({ withActions = false }: { withActions?: boolean }) {
  return (
    <div className="mb-6 flex items-end justify-between gap-3">
      <div className="grid gap-2">
        <Skeleton className="h-3 w-24" />
        <Skeleton className="h-8 w-56 md:h-9" />
        <Skeleton className="h-4 w-72 max-w-[70vw]" />
      </div>
      {withActions && <Skeleton className="h-9 w-28 rounded-[10px]" />}
    </div>
  );
}

/** 52 px player/match rows with stripe, badge, two-line text and a trailing stat. */
export function RowsSkeleton({ rows = 6, className }: { rows?: number; className?: string }) {
  return (
    <div className={cn("overflow-hidden rounded-xl border border-border bg-card", className)}>
      {Array.from({ length: rows }, (_, i) => (
        <div key={i} className="flex h-[52px] items-center gap-3 border-b border-border px-3 last:border-b-0">
          <Skeleton className="h-9 w-[3px] rounded-full" />
          <Skeleton className="h-6 w-9 rounded-full" />
          <div className="grid flex-1 gap-1.5">
            <Skeleton className="h-2.5 w-3/5" />
            <Skeleton className="h-2 w-2/5" />
          </div>
          <Skeleton className="h-2.5 w-10" />
        </div>
      ))}
    </div>
  );
}

/** Sticky-header stat table: 36 px header + 36 px rows. */
export function TableSkeleton({ rows = 10, cols = 7, className }: { rows?: number; cols?: number; className?: string }) {
  return (
    <div className={cn("overflow-hidden rounded-xl border border-border bg-card", className)}>
      <div className="flex h-9 items-center gap-4 border-b border-border bg-surface-2 px-4">
        {Array.from({ length: cols }, (_, i) => (
          <Skeleton key={i} className={cn("h-2", i === 0 ? "w-24 flex-[2]" : "flex-1")} />
        ))}
      </div>
      {Array.from({ length: rows }, (_, r) => (
        <div key={r} className="flex h-9 items-center gap-4 border-b border-border px-4 last:border-b-0">
          {Array.from({ length: cols }, (_, i) =>
            i === 0 ? (
              <div key={i} className="flex flex-[2] items-center gap-2">
                <Skeleton className="h-6 w-9 rounded-full" />
                <Skeleton className="h-2.5 w-16" />
              </div>
            ) : (
              <Skeleton key={i} className="h-2.5 flex-1" />
            ),
          )}
        </div>
      ))}
    </div>
  );
}

export function TilesSkeleton({ count = 4, className }: { count?: number; className?: string }) {
  return (
    <div className={cn("grid grid-cols-2 gap-3 md:grid-cols-4 md:gap-4", className)}>
      {Array.from({ length: count }, (_, i) => (
        <div key={i} className="rounded-lg border border-border bg-card p-3 md:p-4">
          <Skeleton className="h-2 w-16" />
          <Skeleton className="mt-3 h-7 w-20" />
          <Skeleton className="mt-2 h-2 w-24" />
        </div>
      ))}
    </div>
  );
}

export function ChartSkeleton({ className }: { className?: string }) {
  return (
    <div className={cn("rounded-xl border border-border bg-card p-3 md:p-4", className)}>
      <Skeleton className="h-2.5 w-24" />
      <Skeleton className="mt-4 h-56 w-full md:h-64" />
    </div>
  );
}

export function TabsSkeleton({ tabs = 5 }: { tabs?: number }) {
  return (
    <div className="mb-4 flex gap-2 overflow-hidden border-b border-border pb-2">
      {Array.from({ length: tabs }, (_, i) => (
        <Skeleton key={i} className="h-7 w-20 shrink-0 rounded-lg" />
      ))}
    </div>
  );
}

/* ---------- Page-level presets ---------- */

export function ListPageSkeleton({ label = "Loading" }: { label?: string }) {
  return (
    <Busy label={label}>
      <HeaderSkeleton withActions />
      <RowsSkeleton rows={8} />
    </Busy>
  );
}

export function TablePageSkeleton({ label = "Loading table" }: { label?: string }) {
  return (
    <Busy label={label}>
      <HeaderSkeleton withActions />
      <TabsSkeleton tabs={3} />
      <div className="grid gap-4 lg:grid-cols-12">
        <TableSkeleton className="lg:col-span-8" />
        <div className="grid gap-4 lg:col-span-4">
          <RowsSkeleton rows={4} />
        </div>
      </div>
    </Busy>
  );
}

export function ProfilePageSkeleton({ label = "Loading profile" }: { label?: string }) {
  return (
    <Busy label={label}>
      <div className="mb-6 flex items-center gap-4">
        <Skeleton className="size-14 rounded-full" />
        <div className="grid gap-2">
          <Skeleton className="h-8 w-56" />
          <Skeleton className="h-3 w-40" />
        </div>
      </div>
      <TilesSkeleton />
      <div className="mt-6">
        <TabsSkeleton tabs={6} />
      </div>
      <div className="grid gap-4 lg:grid-cols-12">
        <div className="grid gap-4 lg:col-span-8">
          <ChartSkeleton />
          <RowsSkeleton rows={5} />
        </div>
        <RowsSkeleton rows={4} className="lg:col-span-4 lg:self-start" />
      </div>
    </Busy>
  );
}

export function MatchPageSkeleton() {
  return (
    <Busy label="Loading match">
      <div className="mb-4 rounded-xl border border-border bg-card p-4">
        <div className="flex items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <Skeleton className="size-10 rounded-full" />
            <Skeleton className="h-10 w-24" />
          </div>
          <Skeleton className="h-3 w-8" />
          <div className="flex items-center gap-3">
            <Skeleton className="h-10 w-24" />
            <Skeleton className="size-10 rounded-full" />
          </div>
        </div>
        <Skeleton className="mx-auto mt-4 h-3 w-60" />
      </div>
      <TabsSkeleton tabs={8} />
      <div className="grid gap-4 lg:grid-cols-12">
        <ChartSkeleton className="lg:col-span-8" />
        <RowsSkeleton rows={4} className="lg:col-span-4 lg:self-start" />
      </div>
    </Busy>
  );
}

export function HomePageSkeleton() {
  return (
    <Busy label="Loading home">
      <Skeleton className="mb-4 h-3 w-48" />
      <div className="grid gap-4 lg:grid-cols-12">
        <Skeleton className="h-64 rounded-xl lg:col-span-8" />
        <RowsSkeleton rows={4} className="lg:col-span-4" />
      </div>
      <TilesSkeleton className="mt-4" count={4} />
    </Busy>
  );
}

export function GridPageSkeleton({ label = "Loading", count = 10 }: { label?: string; count?: number }) {
  return (
    <Busy label={label}>
      <HeaderSkeleton />
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
        {Array.from({ length: count }, (_, i) => (
          <div key={i} className="flex h-[72px] items-center gap-3 rounded-xl border border-border bg-card px-4">
            <Skeleton className="size-10 rounded-full" />
            <div className="grid flex-1 gap-1.5">
              <Skeleton className="h-3 w-3/4" />
              <Skeleton className="h-2 w-1/2" />
            </div>
          </div>
        ))}
      </div>
    </Busy>
  );
}
