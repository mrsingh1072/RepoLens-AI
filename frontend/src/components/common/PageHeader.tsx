import type { ReactNode } from "react";
import { motion } from "framer-motion";

import { Overline } from "@/components/common/Overline";
import { fadeInUp } from "@/utils/motion";

interface PageHeaderProps {
  /** Mono blueprint annotation above the title, e.g. "WORKSPACE". */
  overline?: string;
  title: string;
  description?: string;
  actions?: ReactNode;
}

/** Page heading: mono overline + display-face title. */
export function PageHeader({ overline, title, description, actions }: PageHeaderProps) {
  return (
    <motion.div
      variants={fadeInUp}
      initial="hidden"
      animate="show"
      className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between"
    >
      <div className="min-w-0">
        {overline && <Overline className="mb-2">{overline}</Overline>}
        <h1 className="font-display text-[32px] font-semibold leading-[1.15] tracking-tight text-ink">
          {title}
        </h1>
        {description && <p className="mt-1.5 max-w-2xl text-sm leading-relaxed text-ink-2">{description}</p>}
      </div>
      {actions && <div className="flex shrink-0 items-center gap-2">{actions}</div>}
    </motion.div>
  );
}
