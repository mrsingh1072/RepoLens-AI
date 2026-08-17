import { AnimatePresence, motion } from "framer-motion";
import { Menu, X } from "lucide-react";
import { NavLink } from "react-router-dom";

import { Logo } from "@/components/common/Logo";
import { Button } from "@/components/ui/button";
import { navItems } from "@/components/layout/navigation";
import { useAppStore } from "@/store/appStore";
import { cn } from "@/utils/cn";
import { settle } from "@/utils/motion";

/** Mobile navigation — a scrim drawer sliding in from the left. */
export function MobileNav() {
  const open = useAppStore((s) => s.mobileNavOpen);
  const setOpen = useAppStore((s) => s.setMobileNavOpen);

  return (
    <>
      <Button
        type="button"
        variant="ghost"
        size="icon"
        className="md:hidden"
        aria-label={open ? "Close navigation menu" : "Open navigation menu"}
        aria-expanded={open}
        aria-controls="mobile-nav-panel"
        onClick={() => setOpen(!open)}
      >
        {open ? <X /> : <Menu />}
      </Button>

      <AnimatePresence>
        {open && (
          <div className="fixed inset-0 z-50 md:hidden" role="presentation">
            <motion.button
              type="button"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="absolute inset-0 bg-bedrock/70 backdrop-blur-[8px]"
              aria-label="Close navigation menu"
              onClick={() => setOpen(false)}
            />
            <motion.aside
              id="mobile-nav-panel"
              role="dialog"
              aria-modal="true"
              aria-label="Main navigation"
              initial={{ x: -40, opacity: 0 }}
              animate={{ x: 0, opacity: 1 }}
              exit={{ x: -40, opacity: 0 }}
              transition={settle}
              className="absolute left-0 top-0 flex h-full w-[min(88vw,20rem)] flex-col border-r border-edge bg-surface"
            >
              <div className="flex h-16 items-center border-b border-edge px-5">
                <Logo to="/" />
              </div>
              <nav className="flex-1 space-y-0.5 overflow-y-auto p-3" aria-label="Primary">
                <span className="overline-label block px-3 pb-2 pt-1">Workspace</span>
                {navItems.map((item) => (
                  <NavLink
                    key={item.to}
                    to={item.to}
                    onClick={() => setOpen(false)}
                    className={({ isActive }) =>
                      cn(
                        "relative flex items-center gap-3 rounded-md px-3 py-2.5 text-sm font-medium transition-colors",
                        isActive ? "bg-raised text-ink" : "text-ink-2 hover:bg-raised/60 hover:text-ink",
                      )
                    }
                  >
                    {({ isActive }) => (
                      <>
                        {isActive && (
                          <span className="absolute left-0 top-1/2 h-5 w-0.5 -translate-y-1/2 rounded-r-full bg-ember" />
                        )}
                        <item.icon
                          className={cn("h-[17px] w-[17px]", isActive ? "text-ember" : "text-ink-3")}
                          aria-hidden
                        />
                        {item.label}
                      </>
                    )}
                  </NavLink>
                ))}
              </nav>
            </motion.aside>
          </div>
        )}
      </AnimatePresence>
    </>
  );
}
