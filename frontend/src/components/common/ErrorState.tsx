import { AlertTriangle, RefreshCw } from "lucide-react";
import { motion } from "framer-motion";

import { BlueprintCorners } from "@/components/common/BlueprintCorners";
import { Button } from "@/components/ui/button";
import { scaleIn } from "@/utils/motion";

interface ErrorStateProps {
  title?: string;
  description?: string;
  onRetry?: () => void;
}

/** Error surface — a displaced stratum. Rust appears as accent, not fill. */
export function ErrorState({
  title = "Something went wrong",
  description = "We couldn't load this data. Please try again.",
  onRetry,
}: ErrorStateProps) {
  return (
    <motion.div
      variants={scaleIn}
      initial="hidden"
      animate="show"
      className="relative flex flex-col items-center justify-center rounded-lg border border-dashed border-edge px-6 py-16 text-center"
    >
      <BlueprintCorners />
      <span className="overline-label mb-5 text-rust">ERR · LOAD FAILED</span>
      <div className="mb-4 flex h-14 w-14 items-center justify-center rounded-lg border border-rust/30 bg-raised text-rust shadow-stratum [&_svg]:size-6">
        <AlertTriangle />
      </div>
      <h3 className="font-display text-lg font-semibold text-ink">{title}</h3>
      <p className="mt-1.5 max-w-sm text-sm leading-relaxed text-ink-2">{description}</p>
      {onRetry && (
        <Button variant="secondary" className="mt-6" onClick={onRetry}>
          <RefreshCw />
          Try again
        </Button>
      )}
    </motion.div>
  );
}
