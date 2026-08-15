import type { ReactNode } from "react";

import { cn } from "@/utils/cn";

/**
 * Signature typographic device: the mono overline. Every section, card,
 * and panel is annotated like an engineer's blueprint.
 */
export function Overline({ children, className }: { children: ReactNode; className?: string }) {
  return <span className={cn("overline-label block", className)}>{children}</span>;
}
