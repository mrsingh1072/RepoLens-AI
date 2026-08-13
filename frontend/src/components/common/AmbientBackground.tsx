import { cn } from "@/utils/cn";

/*
 * Ambient bedrock — the app background is material, not flat:
 *   1. static SVG grain at ~2% opacity,
 *   2. a faint warm vignette from the top (the overhead light source),
 *   3. one very slow ember thermal drifting near the top of the viewport.
 * Felt, never watched. Purely decorative.
 */

const GRAIN =
  "url(\"data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='160' height='160'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='2' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)' opacity='0.5'/%3E%3C/svg%3E\")";

export function AmbientBackground({ className }: { className?: string }) {
  return (
    <div
      className={cn("pointer-events-none absolute inset-0 -z-10 overflow-hidden", className)}
      aria-hidden
    >
      {/* Warm vignette from above — the light source. */}
      <div className="absolute inset-x-0 top-0 h-[42rem] bg-[radial-gradient(80%_60%_at_50%_0%,hsl(30_30%_40%/0.08),transparent_70%)]" />
      {/* One slow ember thermal. */}
      <div className="absolute -top-40 left-1/2 h-[30rem] w-[44rem] -translate-x-1/2 animate-thermal rounded-full bg-[radial-gradient(closest-side,hsl(var(--ember)/0.05),transparent)]" />
      {/* Grain. */}
      <div className="absolute inset-0 opacity-[0.02]" style={{ backgroundImage: GRAIN }} />
    </div>
  );
}
