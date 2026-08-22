import { motion, useReducedMotion } from "framer-motion";
import { Link } from "react-router-dom";

import { AmbientBackground } from "@/components/common/AmbientBackground";
import { Button } from "@/components/ui/button";

/*
 * 404 — the missing stratum. A column of layers with one displaced,
 * annotated in mono like a survey drawing.
 */
export function NotFoundPage() {
  const reduceMotion = useReducedMotion();

  const layers = [
    { width: 180, offset: 0 },
    { width: 180, offset: 0 },
    { width: 180, offset: reduceMotion ? 0 : 42, missing: true },
    { width: 180, offset: 0 },
    { width: 180, offset: 0 },
  ];

  return (
    <div className="relative flex min-h-screen flex-col items-center justify-center overflow-hidden bg-bedrock px-6 text-center">
      <AmbientBackground />

      <div className="mb-10 flex flex-col items-center gap-2" aria-hidden>
        {layers.map((layer, i) => (
          <motion.div
            key={i}
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0, x: layer.offset }}
            transition={{ delay: i * 0.07, type: "spring", stiffness: 300, damping: 26 }}
            className={
              layer.missing
                ? "h-4 rounded-full border border-dashed border-ember/60"
                : "h-4 rounded-full bg-raised shadow-stratum"
            }
            style={{ width: layer.width }}
          />
        ))}
      </div>

      <p className="overline-label text-ember">ERR · 404 · STRATUM NOT FOUND</p>
      <h1 className="mt-4 font-display text-4xl font-semibold tracking-tight text-ink">
        This layer doesn't exist
      </h1>
      <p className="mt-3 max-w-sm text-sm leading-relaxed text-ink-2">
        The page you're looking for was never indexed, or it has eroded away.
      </p>
      <Button variant="secondary" className="mt-8" asChild>
        <Link to="/dashboard">Back to dashboard</Link>
      </Button>
    </div>
  );
}
