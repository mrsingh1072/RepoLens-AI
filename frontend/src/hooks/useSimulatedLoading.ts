import { useCallback, useEffect, useState } from "react";

export type LoadState = "loading" | "success" | "error";

interface Options {
  /** Milliseconds before resolving. */
  delay?: number;
  /** When true, resolves into the error state (for demoing error UIs). */
  shouldFail?: boolean;
}

/**
 * Drives loading/success/error states for demo pages. Mirrors the shape a real
 * data hook would expose so pages are trivial to wire to the backend later.
 */
export function useSimulatedLoading({ delay = 900, shouldFail = false }: Options = {}) {
  const [state, setState] = useState<LoadState>("loading");
  const [tick, setTick] = useState(0);

  const retry = useCallback(() => {
    setState("loading");
    setTick((t) => t + 1);
  }, []);

  useEffect(() => {
    setState("loading");
    const timer = setTimeout(() => setState(shouldFail ? "error" : "success"), delay);
    return () => clearTimeout(timer);
  }, [delay, shouldFail, tick]);

  return { state, retry, isLoading: state === "loading" };
}
