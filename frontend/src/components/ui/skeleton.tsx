import { cn } from "@/utils/cn";

/**
 * Loading placeholder — raised stratum with a slow warm shimmer.
 * Skeleton layouts must match the real content's geometry exactly.
 */
function Skeleton({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div className={cn("relative overflow-hidden rounded-md bg-raised", className)} {...props}>
      <div className="absolute inset-0 -translate-x-full animate-shimmer bg-gradient-to-r from-transparent via-[hsl(36_20%_93%/0.05)] to-transparent" />
    </div>
  );
}

export { Skeleton };
