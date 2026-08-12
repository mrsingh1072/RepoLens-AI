import { cn } from "@/utils/cn";

type Variant = "loading" | "success" | "error";

interface HealthBadgeProps {
  variant: Variant;
  label: string;
}

const DOT_STYLES: Record<Variant, string> = {
  loading: "animate-breathe bg-ember",
  success: "bg-moss",
  error: "bg-rust",
};

/** Small status pill used to surface backend connectivity. */
export function HealthBadge({ variant, label }: HealthBadgeProps) {
  return (
    <span className="inline-flex items-center gap-2 rounded-full border border-edge bg-raised px-3 py-1 font-mono text-xs text-ink-2">
      <span className={cn("h-1.5 w-1.5 rounded-full", DOT_STYLES[variant])} />
      {label}
    </span>
  );
}
