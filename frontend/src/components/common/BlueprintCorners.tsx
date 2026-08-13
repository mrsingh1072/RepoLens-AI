import { cn } from "@/utils/cn";

/**
 * Blueprint corner ticks — small `+` marks at the corners of hero
 * surfaces and empty states. Part of the engineer's-drawing motif.
 */
export function BlueprintCorners({ className }: { className?: string }) {
  const positions = [
    "-left-[5px] -top-[5px]",
    "-right-[5px] -top-[5px]",
    "-left-[5px] -bottom-[5px]",
    "-right-[5px] -bottom-[5px]",
  ];
  return (
    <div className={cn("pointer-events-none absolute inset-0", className)} aria-hidden>
      {positions.map((pos) => (
        <svg
          key={pos}
          viewBox="0 0 10 10"
          className={cn("absolute h-2.5 w-2.5 text-ink-3", pos)}
          fill="none"
          stroke="currentColor"
          strokeWidth="1"
        >
          <path d="M5 0v10M0 5h10" />
        </svg>
      ))}
    </div>
  );
}
