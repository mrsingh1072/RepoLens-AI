import type { ReactNode } from "react";
import { motion } from "framer-motion";

import { BlueprintCorners } from "@/components/common/BlueprintCorners";
import { scaleIn } from "@/utils/motion";

interface EmptyStateProps {
  icon: ReactNode;
  title: string;
  description: string;
  action?: ReactNode;
  /** Mono annotation, e.g. "EMPTY · NO REPOSITORIES". */
  overline?: string;
}

/** Empty state: blueprint corners, one explanation, one action. */
export function EmptyState({ icon, title, description, action, overline }: EmptyStateProps) {
  return (
    <motion.div
      variants={scaleIn}
      initial="hidden"
      animate="show"
      className="relative flex flex-col items-center justify-center rounded-lg border border-dashed border-edge px-6 py-16 text-center"
    >
      <BlueprintCorners />
      {overline && <span className="overline-label mb-5">{overline}</span>}
      <div className="mb-4 flex h-14 w-14 items-center justify-center rounded-lg border border-edge bg-raised text-ink-3 shadow-stratum [&_svg]:size-6">
        {icon}
      </div>
      <h3 className="font-display text-lg font-semibold text-ink">{title}</h3>
      <p className="mt-1.5 max-w-sm text-sm leading-relaxed text-ink-2">{description}</p>
      {action && <div className="mt-6">{action}</div>}
    </motion.div>
  );
}
