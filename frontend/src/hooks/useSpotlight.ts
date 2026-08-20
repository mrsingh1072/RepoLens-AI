import { useCallback, useRef } from "react";

/**
 * Ember spotlight — interactive surfaces track the cursor with a warm
 * radial wash (see `.spotlight` in index.css). CSS-variable driven so it
 * costs nothing on the React render path.
 */
export function useSpotlight<T extends HTMLElement = HTMLDivElement>() {
  const ref = useRef<T>(null);

  const onPointerMove = useCallback((e: React.PointerEvent<T>) => {
    const el = ref.current;
    if (!el) return;
    const rect = el.getBoundingClientRect();
    el.style.setProperty("--spot-x", `${e.clientX - rect.left}px`);
    el.style.setProperty("--spot-y", `${e.clientY - rect.top}px`);
    el.style.setProperty("--spot-opacity", "1");
  }, []);

  const onPointerLeave = useCallback(() => {
    ref.current?.style.setProperty("--spot-opacity", "0");
  }, []);

  return { ref, onPointerMove, onPointerLeave };
}
