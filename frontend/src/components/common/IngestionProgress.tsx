import { motion } from "framer-motion";
import { Check, X } from "lucide-react";

import { Card } from "@/components/ui/card";
import { Overline } from "@/components/common/Overline";
import type { IngestionJob, IngestionStage } from "@/types/ingestion";
import { cn } from "@/utils/cn";
import { settle } from "@/utils/motion";

/*
 * The machine at work — ingestion as excavation. Six strata fill from the
 * top down: the active layer carries an ember scan-line and breathes; a
 * finished layer flashes moss, then settles. Everything idle stays stone.
 */

const PIPELINE_STEPS: { stage: IngestionStage; label: string; detail: string }[] = [
  { stage: "validating", label: "Validate", detail: "Verify source and access" },
  { stage: "cloning", label: "Clone", detail: "Fetch working tree" },
  { stage: "parsing", label: "Parse", detail: "Tree-sitter symbol extraction" },
  { stage: "graphing", label: "Graph", detail: "Build knowledge graph" },
  { stage: "indexing", label: "Index", detail: "Persist symbols and chunks" },
  { stage: "embedding", label: "Embed", detail: "Vector embeddings" },
];

const STAGE_ORDER: IngestionStage[] = [
  "queued",
  "validating",
  "cloning",
  "parsing",
  "graphing",
  "indexing",
  "embedding",
  "completed",
];

function stageIndex(stage: IngestionStage): number {
  const idx = STAGE_ORDER.indexOf(stage);
  return idx === -1 ? STAGE_ORDER.indexOf("parsing") : idx;
}

interface IngestionProgressProps {
  job: IngestionJob;
  className?: string;
}

export function IngestionProgress({ job, className }: IngestionProgressProps) {
  const currentIdx = stageIndex(job.stage);
  const failed = job.stage === "failed";
  const completed = job.stage === "completed";

  return (
    <Card className={cn("overflow-hidden p-6", className)}>
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0">
          <Overline className={cn(failed ? "text-rust" : completed ? "text-moss" : "text-ember")}>
            {failed
              ? "INGESTION · FAILED"
              : completed
                ? "INGESTION · COMPLETE"
                : `INGESTION · STAGE ${Math.min(Math.max(currentIdx, 1), 6)}/6`}
          </Overline>
          <p className="mt-2 truncate font-mono text-[13px] text-ink-2" aria-live="polite">
            {job.message}
          </p>
        </div>
        <span
          className={cn(
            "tnum shrink-0 font-display text-3xl font-semibold leading-none tracking-tight",
            failed ? "text-rust" : completed ? "text-moss" : "animate-breathe text-ember",
          )}
        >
          {job.progress}%
        </span>
      </div>

      {/* Overall progress — a thin seam of heat. */}
      <div className="mt-5 h-1 overflow-hidden rounded-full bg-raised">
        <motion.div
          className={cn("h-full rounded-full", failed ? "bg-rust" : completed ? "bg-moss" : "bg-ember")}
          initial={{ width: 0 }}
          animate={{ width: `${job.progress}%` }}
          transition={settle}
        />
      </div>

      {/* The strata column. */}
      <ol className="mt-6 space-y-1.5">
        {PIPELINE_STEPS.map((step) => {
          const stepIdx = stageIndex(step.stage);
          const done = !failed && (completed || currentIdx > stepIdx);
          const active = !failed && job.stage === step.stage;
          const stepFailed = failed && currentIdx === stepIdx;

          return (
            <li
              key={step.stage}
              className={cn(
                "relative flex items-center gap-3 overflow-hidden rounded-md border px-3.5 py-2.5 transition-colors duration-300",
                active && "border-ember/40 bg-raised",
                done && "border-edge bg-surface",
                stepFailed && "border-rust/40 bg-raised",
                !active && !done && !stepFailed && "border-transparent bg-transparent",
              )}
            >
              {/* Ember scan-line across the active layer. */}
              {active && (
                <span
                  aria-hidden
                  className="absolute inset-y-0 left-0 w-1/3 animate-scan bg-gradient-to-r from-transparent via-[hsl(var(--ember)/0.12)] to-transparent"
                />
              )}

              <span
                className={cn(
                  "flex h-5 w-5 shrink-0 items-center justify-center rounded-full border text-[10px]",
                  done && "border-moss/50 bg-moss/15 text-moss",
                  active && "animate-breathe border-ember bg-ember/15 text-ember",
                  stepFailed && "border-rust/50 bg-rust/15 text-rust",
                  !done && !active && !stepFailed && "border-edge text-ink-3",
                )}
              >
                {done ? (
                  <Check className="h-3 w-3" strokeWidth={3} />
                ) : stepFailed ? (
                  <X className="h-3 w-3" strokeWidth={3} />
                ) : (
                  <span className={cn("h-1.5 w-1.5 rounded-full", active ? "bg-ember" : "bg-ink-3/50")} />
                )}
              </span>

              <span
                className={cn(
                  "text-sm font-medium",
                  active ? "text-ink" : done ? "text-ink-2" : stepFailed ? "text-rust" : "text-ink-3",
                )}
              >
                {step.label}
              </span>
              <span className="ml-auto hidden font-mono text-[11px] text-ink-3 sm:block">
                {step.detail}
              </span>
            </li>
          );
        })}
      </ol>

      {failed && job.error && (
        <p className="mt-4 rounded-md border border-rust/25 bg-raised px-3.5 py-2.5 font-mono text-[13px] text-rust">
          {job.error}
        </p>
      )}
    </Card>
  );
}
