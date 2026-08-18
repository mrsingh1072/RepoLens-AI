import * as React from "react";
import { Slot } from "@radix-ui/react-slot";
import { cva, type VariantProps } from "class-variance-authority";

import { cn } from "@/utils/cn";

/*
 * STRATA buttons. One ember-filled primary per view; everything else is
 * stone. All buttons compress on press (scale 0.98, "snap" feel).
 */
const buttonVariants = cva(
  "inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-md text-sm font-medium transition-[transform,background-color,border-color,box-shadow,color] duration-150 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-bedrock disabled:pointer-events-none disabled:opacity-50 [&_svg]:size-4 [&_svg]:shrink-0 active:scale-[0.98]",
  {
    variants: {
      variant: {
        // Heat: dark ink on ember, subtle glow.
        default:
          "bg-ember text-on-ember shadow-ember-glow hover:bg-ember-bright",
        secondary:
          "border border-edge bg-raised text-ink shadow-stratum hover:border-edge-strong hover:bg-overlay",
        ghost: "text-ink-2 hover:bg-raised hover:text-ink",
        outline:
          "border border-edge bg-transparent text-ink hover:border-edge-strong hover:bg-raised",
        // Rust outline that fills on hover — destructive is never loud at rest.
        destructive:
          "border border-rust/40 bg-transparent text-rust hover:bg-rust hover:text-ink hover:border-rust",
        link: "text-ember underline-offset-4 hover:underline",
      },
      size: {
        default: "h-10 px-4 py-2",
        sm: "h-8 rounded-sm px-3 text-[13px]",
        lg: "h-12 rounded-md px-6 text-base",
        icon: "h-10 w-10",
        "icon-sm": "h-8 w-8 rounded-sm",
      },
    },
    defaultVariants: { variant: "default", size: "default" },
  },
);

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  asChild?: boolean;
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, asChild = false, ...props }, ref) => {
    const Comp = asChild ? Slot : "button";
    return (
      <Comp className={cn(buttonVariants({ variant, size }), className)} ref={ref} {...props} />
    );
  },
);
Button.displayName = "Button";

export { Button, buttonVariants };
