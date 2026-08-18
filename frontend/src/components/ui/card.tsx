import * as React from "react";

import { cn } from "@/utils/cn";
import { useSpotlight } from "@/hooks/useSpotlight";

/** Static card surface: deep zinc fill, hairline border, top highlight. */
const Card = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => (
    <div
      ref={ref}
      className={cn(
        "rounded-xl border border-white/5 bg-zinc-900/30 shadow-[inset_0_1px_0_0_rgba(255,255,255,0.05)]",
        className,
      )}
      {...props}
    />
  ),
);
Card.displayName = "Card";

/**
 * Interactive stratum: tracks the cursor with an ember spotlight and
 * rises 2px on hover. Use for anything clickable.
 */
const SpotlightCard = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  ({ className, children, ...props }, forwardedRef) => {
    const { ref, onPointerMove, onPointerLeave } = useSpotlight<HTMLDivElement>();

    return (
      <div
        ref={(node) => {
          (ref as React.MutableRefObject<HTMLDivElement | null>).current = node;
          if (typeof forwardedRef === "function") forwardedRef(node);
          else if (forwardedRef) forwardedRef.current = node;
        }}
        onPointerMove={onPointerMove}
        onPointerLeave={onPointerLeave}
        className={cn(
          "spotlight relative rounded-xl border border-white/5 bg-zinc-900/30 shadow-[inset_0_1px_0_0_rgba(255,255,255,0.05)]",
          "transition-all duration-200 hover:border-zinc-700/50 hover:bg-zinc-900/50",
          className,
        )}
        {...props}
      >
        {children}
      </div>
    );
  },
);
SpotlightCard.displayName = "SpotlightCard";

const CardHeader = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => (
    <div ref={ref} className={cn("flex flex-col space-y-1.5 p-6", className)} {...props} />
  ),
);
CardHeader.displayName = "CardHeader";

const CardTitle = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => (
    <div ref={ref} className={cn("font-semibold leading-none tracking-tight", className)} {...props} />
  ),
);
CardTitle.displayName = "CardTitle";

const CardDescription = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => (
    <div ref={ref} className={cn("text-sm text-ink-2", className)} {...props} />
  ),
);
CardDescription.displayName = "CardDescription";

const CardContent = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => (
    <div ref={ref} className={cn("p-6 pt-0", className)} {...props} />
  ),
);
CardContent.displayName = "CardContent";

const CardFooter = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => (
    <div ref={ref} className={cn("flex items-center p-6 pt-0", className)} {...props} />
  ),
);
CardFooter.displayName = "CardFooter";

export { Card, SpotlightCard, CardHeader, CardTitle, CardDescription, CardContent, CardFooter };
