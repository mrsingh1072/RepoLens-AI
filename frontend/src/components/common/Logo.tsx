import { Link } from "react-router-dom";

import { cn } from "@/utils/cn";

interface LogoProps {
  className?: string;
  showWordmark?: boolean;
  /** When set, the logo links to this route (e.g. home). */
  to?: string;
}

/**
 * Brand mark: three strata — layers of rock, the top one glowing ember.
 * A codebase is a geological object; we excavate it.
 */
function Glyph() {
  return (
    <div className="relative flex h-8 w-8 items-center justify-center rounded-md border border-edge bg-raised shadow-stratum">
      <svg viewBox="0 0 20 20" style={{ width: 18, height: 18 }} aria-hidden>
        <rect x="3" y="4" width="14" height="3" rx="1.5" fill="hsl(var(--ember))" />
        <rect x="3" y="9" width="14" height="3" rx="1.5" fill="hsl(var(--text-2))" opacity="0.7" />
        <rect x="3" y="14" width="14" height="3" rx="1.5" fill="hsl(var(--text-3))" opacity="0.55" />
      </svg>
    </div>
  );
}

export function Logo({ className, showWordmark = true, to }: LogoProps) {
  const content = (
    <>
      <Glyph />
      {showWordmark && (
        <span className="font-display text-[15px] font-semibold tracking-tight text-ink">
          RepoLens AI
        </span>
      )}
    </>
  );

  if (to) {
    return (
      <Link
        to={to}
        className={cn("flex items-center gap-2.5 transition-opacity hover:opacity-85", className)}
        aria-label="RepoLens AI home"
      >
        {content}
      </Link>
    );
  }

  return <div className={cn("flex items-center gap-2.5", className)}>{content}</div>;
}
