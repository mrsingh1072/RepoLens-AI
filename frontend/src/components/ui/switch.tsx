import * as React from "react";
import * as SwitchPrimitives from "@radix-ui/react-switch";

import { cn } from "@/utils/cn";

const Switch = React.forwardRef<
  React.ElementRef<typeof SwitchPrimitives.Root>,
  React.ComponentPropsWithoutRef<typeof SwitchPrimitives.Root>
>(({ className, ...props }, ref) => (
  <SwitchPrimitives.Root
    ref={ref}
    className={cn(
      "peer inline-flex h-6 w-11 shrink-0 cursor-pointer items-center rounded-full border border-edge transition-colors",
      "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-bedrock",
      "disabled:cursor-not-allowed disabled:opacity-50",
      "data-[state=checked]:border-ember data-[state=checked]:bg-ember data-[state=unchecked]:bg-raised",
      className,
    )}
    {...props}
  >
    <SwitchPrimitives.Thumb
      className={cn(
        "pointer-events-none block h-[18px] w-[18px] rounded-full shadow-sm ring-0 transition-transform",
        "data-[state=checked]:translate-x-[22px] data-[state=checked]:bg-on-ember data-[state=unchecked]:translate-x-[3px] data-[state=unchecked]:bg-ink-2",
      )}
    />
  </SwitchPrimitives.Root>
));
Switch.displayName = SwitchPrimitives.Root.displayName;

export { Switch };
