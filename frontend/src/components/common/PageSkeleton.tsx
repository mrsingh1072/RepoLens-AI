import { Skeleton } from "@/components/ui/skeleton";

/** Route-level loading placeholder; geometry mirrors a typical page. */
export function PageSkeleton() {
  return (
    <div className="space-y-8 animate-in fade-in duration-300" aria-busy="true" aria-label="Loading page">
      <div className="space-y-2.5">
        <Skeleton className="h-3 w-28" />
        <Skeleton className="h-9 w-64" />
        <Skeleton className="h-4 w-96 max-w-full" />
      </div>
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <Skeleton key={i} className="h-[108px] rounded-lg" />
        ))}
      </div>
      <Skeleton className="h-[420px] rounded-lg" />
    </div>
  );
}
