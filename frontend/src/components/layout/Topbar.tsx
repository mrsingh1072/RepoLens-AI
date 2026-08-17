import { Moon, Search, Sun } from "lucide-react";

import { Button } from "@/components/ui/button";
import { MobileNav } from "@/components/layout/MobileNav";
import { useAppStore } from "@/store/appStore";

/** Top bar: centered command-palette trigger and theme toggle. */
export function Topbar() {
  const theme = useAppStore((s) => s.theme);
  const toggleTheme = useAppStore((s) => s.toggleTheme);
  const setCommandOpen = useAppStore((s) => s.setCommandOpen);

  return (
    <header className="sticky top-0 z-20 grid h-16 grid-cols-[auto_1fr_auto] items-center gap-2 border-b border-edge bg-bedrock/85 px-3 backdrop-blur-sm md:grid-cols-[1fr_minmax(0,26rem)_1fr] md:gap-3 md:px-6">
      <MobileNav />

      <button
        type="button"
        onClick={() => setCommandOpen(true)}
        aria-label="Open command palette"
        aria-keyshortcuts="Control+K Meta+K"
        className="group flex w-full items-center gap-2.5 rounded-md border border-transparent bg-zinc-900/50 px-4 py-1.5 text-sm text-zinc-300 shadow-[inset_0_1px_4px_rgba(0,0,0,0.5)] transition-colors focus:ring-1 focus:ring-zinc-700 focus-visible:ring-1 focus-visible:ring-zinc-700 focus-visible:ring-offset-0"
      >
        <Search className="h-3.5 w-3.5 shrink-0 text-zinc-500" aria-hidden />
        <span className="flex-1 truncate text-left text-zinc-500">Search or jump to…</span>
        <kbd className="hidden rounded-sm border border-edge bg-surface px-1.5 py-0.5 font-mono text-[10px] tracking-widest text-ink-3 sm:inline">
          ⌘K
        </kbd>
      </button>

      <div className="flex items-center justify-end">
        <Button variant="ghost" size="icon" onClick={toggleTheme} aria-label="Toggle theme">
          {theme === "dark" ? <Sun aria-hidden /> : <Moon aria-hidden />}
        </Button>
      </div>
    </header>
  );
}
