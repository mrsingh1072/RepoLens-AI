import { useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";

import { navItems } from "@/components/layout/navigation";
import { useAppStore } from "@/store/appStore";

function isEditableTarget(target: EventTarget | null): boolean {
  if (!(target instanceof HTMLElement)) return false;
  const tag = target.tagName;
  return (
    tag === "INPUT" ||
    tag === "TEXTAREA" ||
    tag === "SELECT" ||
    target.isContentEditable
  );
}

const NAV_SHORTCUTS = Object.fromEntries(
  navItems
    .filter((item) => item.shortcut)
    .map((item) => {
      const key = item.shortcut!.split(" ").pop()!.toLowerCase();
      return [key, item.to];
    }),
);

/** Global keyboard shortcuts: ⌘K palette, G+key navigation, ? help. */
export function useKeyboardShortcuts() {
  const navigate = useNavigate();
  const setCommandOpen = useAppStore((s) => s.setCommandOpen);
  const pendingG = useRef(false);
  const pendingTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    const clearPending = () => {
      pendingG.current = false;
      if (pendingTimer.current) {
        clearTimeout(pendingTimer.current);
        pendingTimer.current = null;
      }
    };

    const armPendingG = () => {
      pendingG.current = true;
      if (pendingTimer.current) clearTimeout(pendingTimer.current);
      pendingTimer.current = setTimeout(clearPending, 1200);
    };

    const onKeyDown = (event: KeyboardEvent) => {
      if (isEditableTarget(event.target)) return;

      const key = event.key.toLowerCase();

      if (key === "k" && (event.metaKey || event.ctrlKey)) {
        event.preventDefault();
        setCommandOpen(!useAppStore.getState().commandOpen);
        return;
      }

      if (key === "escape") {
        setCommandOpen(false);
        clearPending();
        return;
      }

      if (pendingG.current) {
        const route = NAV_SHORTCUTS[key];
        clearPending();
        if (route) {
          event.preventDefault();
          navigate(route);
        }
        return;
      }

      if (key === "g" && !event.metaKey && !event.ctrlKey && !event.altKey) {
        armPendingG();
        return;
      }

      if (key === "/" && !event.metaKey && !event.ctrlKey) {
        event.preventDefault();
        setCommandOpen(true);
      }
    };

    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("keydown", onKeyDown);
      clearPending();
    };
  }, [navigate, setCommandOpen]);
}
