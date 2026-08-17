import { AnimatePresence, motion } from "framer-motion";
import { ChevronsLeft, PanelLeft } from "lucide-react";
import { NavLink } from "react-router-dom";

import { Logo } from "@/components/common/Logo";
import { Button } from "@/components/ui/button";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";
import { navItems } from "@/components/layout/navigation";
import { useAppStore } from "@/store/appStore";
import { cn } from "@/utils/cn";
import { settle, snap } from "@/utils/motion";

/*
 * Primary sidebar — a stratum standing at the left edge. The active route
 * is marked by a single shared ember rail that slides between items.
 */
export function Sidebar() {
  const collapsed = useAppStore((s) => s.sidebarCollapsed);
  const toggleSidebar = useAppStore((s) => s.toggleSidebar);

  return (
    <motion.aside
      initial={false}
      animate={{ width: collapsed ? 72 : 264 }}
      transition={settle}
      className="sticky top-0 z-30 hidden h-screen shrink-0 flex-col border-r border-edge bg-bedrock md:flex"
    >
      <div className={cn("flex h-16 items-center border-b border-edge px-5", collapsed && "justify-center px-0")}>
        {collapsed ? <Logo showWordmark={false} to="/" /> : <Logo to="/" />}
      </div>

      <TooltipProvider delayDuration={0}>
        <nav className="flex-1 space-y-0.5 overflow-y-auto p-3" aria-label="Primary">
          {!collapsed && <span className="overline-label block px-3 pb-2 pt-1">Workspace</span>}
          {navItems.map((item) => (
            <Tooltip key={item.to}>
              <TooltipTrigger asChild>
                <NavLink
                  to={item.to}
                  className={({ isActive }) =>
                    cn(
                      "group relative flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors",
                      collapsed && "justify-center px-0 py-2.5",
                      isActive
                        ? "bg-zinc-800/50 text-zinc-50"
                        : "text-zinc-400 hover:bg-zinc-900/30 hover:text-zinc-100",
                    )
                  }
                >
                  {({ isActive }) => (
                    <>
                      {isActive && (
                        <motion.span
                          layoutId="sidebar-active"
                          transition={snap}
                          className="absolute left-0 top-1/2 h-5 w-0.5 -translate-y-1/2 rounded-r-full bg-ember"
                        />
                      )}
                      <item.icon
                        className={cn(
                          "h-[17px] w-[17px] shrink-0 transition-colors",
                          isActive ? "text-ember" : "text-ink-3 group-hover:text-ink-2",
                        )}
                      />
                      <AnimatePresence initial={false}>
                        {!collapsed && (
                          <motion.span
                            initial={{ opacity: 0, x: -6 }}
                            animate={{ opacity: 1, x: 0 }}
                            exit={{ opacity: 0, x: -6 }}
                            transition={snap}
                            className="truncate"
                          >
                            {item.label}
                          </motion.span>
                        )}
                      </AnimatePresence>
                      {!collapsed && item.shortcut && (
                        <span className="ml-auto font-mono text-[10px] tracking-widest text-ink-3 opacity-0 transition-opacity group-hover:opacity-100">
                          {item.shortcut}
                        </span>
                      )}
                    </>
                  )}
                </NavLink>
              </TooltipTrigger>
              {collapsed && <TooltipContent side="right">{item.label}</TooltipContent>}
            </Tooltip>
          ))}
        </nav>
      </TooltipProvider>

      <div className="border-t border-edge p-3">
        <Button
          variant="ghost"
          size={collapsed ? "icon" : "default"}
          onClick={toggleSidebar}
          className={cn("w-full justify-start", collapsed && "w-auto justify-center")}
          aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
        >
          {collapsed ? <PanelLeft /> : <ChevronsLeft />}
          {!collapsed && <span>Collapse</span>}
        </Button>
      </div>
    </motion.aside>
  );
}
