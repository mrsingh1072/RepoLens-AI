import { useCallback, useEffect, useState } from "react";

import { getHealth } from "@/api/health";
import { toApiErrorMessage } from "@/api/client";
import type { HealthResponse } from "@/types/health";

type Status = "idle" | "loading" | "success" | "error";

interface UseHealthResult {
  status: Status;
  data: HealthResponse | null;
  error: string | null;
  refetch: () => void;
}

/** Fetch backend health on mount and expose a manual refetch. */
export function useHealth(): UseHealthResult {
  const [status, setStatus] = useState<Status>("idle");
  const [data, setData] = useState<HealthResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setStatus("loading");
    setError(null);
    try {
      const result = await getHealth();
      setData(result);
      setStatus("success");
    } catch (err) {
      setError(toApiErrorMessage(err));
      setStatus("error");
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  return { status, data, error, refetch: () => void load() };
}
