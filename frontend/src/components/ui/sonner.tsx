import { Toaster as Sonner } from "sonner";

import { useAppStore } from "@/store/appStore";

/** Toast host — overlay stratum with an intent rail on the left edge. */
export function Toaster() {
  const theme = useAppStore((s) => s.theme);
  return (
    <Sonner
      theme={theme}
      position="bottom-right"
      toastOptions={{
        classNames: {
          toast:
            "group rounded-lg border border-edge !bg-overlay !text-ink shadow-overlay border-l-2",
          title: "text-sm font-medium",
          description: "!text-ink-2 text-[13px]",
          actionButton: "!bg-ember !text-on-ember",
          cancelButton: "!bg-raised !text-ink-2",
          success: "!border-l-moss [&_[data-icon]]:!text-moss",
          error: "!border-l-rust [&_[data-icon]]:!text-rust",
          warning: "!border-l-gold [&_[data-icon]]:!text-gold",
          info: "!border-l-ember [&_[data-icon]]:!text-ember",
        },
      }}
    />
  );
}
