import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";

import { cn } from "@/utils/cn";

/*
 * Status is never a full-color fill at rest — badges are stone pills with
 * a colored dot + text, so state survives grayscale.
 */
const badgeVariants = cva(
  "inline-flex items-center gap-1.5 rounded-full border border-edge bg-raised px-2.5 py-0.5 text-xs font-medium text-ink-2 transition-colors",
  {
    variants: {
      variant: {
        default: "text-ember",
        secondary: "",
        success: "text-moss",
        warning: "text-gold",
        danger: "text-rust",
        outline: "bg-transparent text-ink",
      },
    },
    defaultVariants: { variant: "default" },
  },
);

const DOT_COLOR: Record<string, string> = {
  default: "bg-ember",
  success: "bg-moss",
  warning: "bg-gold",
  danger: "bg-rust",
};

export interface BadgeProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof badgeVariants> {
  /** Render the status dot (on by default for status variants). */
  dot?: boolean;
}

function Badge({ className, variant, dot, children, ...props }: BadgeProps) {
  const showDot = dot ?? (variant != null && variant in DOT_COLOR);
  return (
    <div className={cn(badgeVariants({ variant }), className)} {...props}>
      {showDot && (
        <span
          className={cn("h-1.5 w-1.5 shrink-0 rounded-full", DOT_COLOR[variant ?? "default"])}
          aria-hidden
        />
      )}
      {children}
    </div>
  );
}

export { Badge, badgeVariants };
