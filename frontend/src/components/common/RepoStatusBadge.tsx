import { Badge } from "@/components/ui/badge";
import { cn } from "@/utils/cn";
import type { RepoStatus } from "@/types";

/*
 * Live heat rule: only a working process breathes. Indexed/queued/failed
 * repos are stone-cold; an indexing repo pulses ember.
 */
const CONFIG: Record<RepoStatus, { label: string; variant: "success" | "warning" | "danger" | "secondary"; live?: boolean }> = {
  indexed: { label: "Indexed", variant: "success" },
  indexing: { label: "Indexing", variant: "warning", live: true },
  queued: { label: "Queued", variant: "secondary" },
  failed: { label: "Failed", variant: "danger" },
};

export function RepoStatusBadge({ status }: { status: RepoStatus }) {
  const { label, variant, live } = CONFIG[status];
  return (
    <Badge variant={variant} dot={variant !== "secondary"} className={cn("font-mono text-[11px]", live && "[&>span]:animate-breathe [&>span]:bg-ember text-ember")}>
      {label}
    </Badge>
  );
}
