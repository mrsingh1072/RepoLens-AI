import type { ReactNode } from "react";
import { motion } from "framer-motion";
import { ArrowDownRight, ArrowUpRight } from "lucide-react";

import { SpotlightCard } from "@/components/ui/card";
import { Overline } from "@/components/common/Overline";
import { cn } from "@/utils/cn";
import { fadeInUp } from "@/utils/motion";

interface StatCardProps {
  label: string;
  value: string;
  icon?: ReactNode;
  /** e.g. "+12%". Positive/negative inferred from the leading sign. */
  delta?: string;
  /** Marks the stat as live — it breathes ember. */
  live?: boolean;
}

/** KPI stratum: mono overline label, big display numeral, optional delta. */
export function StatCard({ label, value, icon, delta, live = false }: StatCardProps) {
  const isNegative = delta?.trim().startsWith("-");

  return (
    <motion.div variants={fadeInUp}>
      <SpotlightCard className="p-5">
        <div className="flex items-start justify-between gap-2">
          <Overline>{label}</Overline>
          {icon && <span className="text-ink-3 [&_svg]:size-4">{icon}</span>}
        </div>
        <div className="mt-3 flex items-baseline gap-2.5">
          <span
            className={cn(
              "tnum font-sans text-[28px] font-semibold leading-none tracking-tight text-ink",
              live && "animate-breathe text-ember",
            )}
          >
            {value}
          </span>
          {delta && (
            <span
              className={cn(
                "tnum inline-flex items-center gap-0.5 font-mono text-xs",
                isNegative ? "text-rust" : "text-moss",
              )}
            >
              {isNegative ? <ArrowDownRight className="h-3 w-3" /> : <ArrowUpRight className="h-3 w-3" />}
              {delta.replace(/^[-+]/, "")}
            </span>
          )}
        </div>
      </SpotlightCard>
    </motion.div>
  );
}
