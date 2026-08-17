import { AnimatePresence, motion } from "framer-motion";
import { Outlet, useLocation } from "react-router-dom";

import { AmbientBackground } from "@/components/common/AmbientBackground";
import { SkipLink } from "@/components/common/SkipLink";
import { CommandPalette } from "@/components/layout/CommandPalette";
import { Sidebar } from "@/components/layout/Sidebar";
import { Topbar } from "@/components/layout/Topbar";
import { useKeyboardShortcuts } from "@/hooks/useKeyboardShortcuts";
import { pageTransition } from "@/utils/motion";

/** Shell for all app pages: sidebar + topbar + animated outlet over the bedrock. */
export function AppLayout() {
  const location = useLocation();
  useKeyboardShortcuts();

  return (
    <div className="relative flex min-h-screen bg-bedrock">
      <SkipLink />
      <AmbientBackground className="fixed" />
      <Sidebar />

      <div className="flex min-w-0 flex-1 flex-col">
        <Topbar />
        <main
          id="main-content"
          tabIndex={-1}
          aria-label="Main content"
          className="flex-1 px-4 py-6 outline-none md:px-8 md:py-8"
        >
          <div className="mx-auto w-full max-w-[1440px]">
            <AnimatePresence mode="wait">
              <motion.div
                key={location.pathname}
                variants={pageTransition}
                initial="hidden"
                animate="show"
                exit="exit"
              >
                <Outlet />
              </motion.div>
            </AnimatePresence>
          </div>
        </main>
      </div>

      <CommandPalette />
    </div>
  );
}
