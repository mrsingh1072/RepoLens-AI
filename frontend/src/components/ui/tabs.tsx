import * as React from "react";
import * as TabsPrimitive from "@radix-ui/react-tabs";
import { motion } from "framer-motion";

import { snap } from "@/utils/motion";
import { cn } from "@/utils/cn";

/*
 * Underline tabs: a shared ember indicator slides between triggers
 * (framer-motion layoutId), rather than re-rendered highlights.
 */

const Tabs = TabsPrimitive.Root;

const TabsList = React.forwardRef<
  React.ElementRef<typeof TabsPrimitive.List>,
  React.ComponentPropsWithoutRef<typeof TabsPrimitive.List>
>(({ className, ...props }, ref) => (
  <TabsPrimitive.List
    ref={ref}
    className={cn(
      "inline-flex h-10 items-center gap-1 border-b border-edge text-ink-2",
      className,
    )}
    {...props}
  />
));
TabsList.displayName = TabsPrimitive.List.displayName;

const TabsIndicatorContext = React.createContext<string>("tabs");

const TabsTrigger = React.forwardRef<
  React.ElementRef<typeof TabsPrimitive.Trigger>,
  React.ComponentPropsWithoutRef<typeof TabsPrimitive.Trigger>
>(({ className, children, ...props }, ref) => {
  const layoutGroup = React.useContext(TabsIndicatorContext);
  const triggerRef = React.useRef<HTMLButtonElement | null>(null);
  const [active, setActive] = React.useState(false);

  // Track data-state without re-implementing Radix internals.
  React.useEffect(() => {
    const el = triggerRef.current;
    if (!el) return;
    const update = () => setActive(el.getAttribute("data-state") === "active");
    update();
    const observer = new MutationObserver(update);
    observer.observe(el, { attributes: true, attributeFilter: ["data-state"] });
    return () => observer.disconnect();
  }, []);

  return (
    <TabsPrimitive.Trigger
      ref={(node) => {
        triggerRef.current = node;
        if (typeof ref === "function") ref(node);
        else if (ref) ref.current = node;
      }}
      className={cn(
        "relative inline-flex h-full items-center justify-center gap-2 whitespace-nowrap px-3 text-sm font-medium transition-colors",
        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:pointer-events-none disabled:opacity-50",
        "text-ink-2 hover:text-ink data-[state=active]:text-ink",
        className,
      )}
      {...props}
    >
      {children}
      {active && (
        <motion.span
          layoutId={`${layoutGroup}-indicator`}
          transition={snap}
          className="absolute inset-x-1 -bottom-px h-0.5 rounded-full bg-ember"
        />
      )}
    </TabsPrimitive.Trigger>
  );
});
TabsTrigger.displayName = TabsPrimitive.Trigger.displayName;

const TabsContent = React.forwardRef<
  React.ElementRef<typeof TabsPrimitive.Content>,
  React.ComponentPropsWithoutRef<typeof TabsPrimitive.Content>
>(({ className, ...props }, ref) => (
  <TabsPrimitive.Content
    ref={ref}
    className={cn(
      "mt-4 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
      className,
    )}
    {...props}
  />
));
TabsContent.displayName = TabsPrimitive.Content.displayName;

export { Tabs, TabsList, TabsTrigger, TabsContent };
