import { useCallback, useEffect, useState } from "react";

import { getParseResults } from "@/api/ingestion";
import { toApiErrorMessage } from "@/api/client";
import type { ParseResultsResponse } from "@/types/parse";

export function useParseResults(jobId: string | null, enabled = true) {
  const [data, setData] = useState<ParseResultsResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const fetchResults = useCallback(async () => {
    if (!jobId || !enabled) return;
    setLoading(true);
    setError(null);
    try {
      const results = await getParseResults(jobId);
      setData(results);
    } catch (err) {
      setError(toApiErrorMessage(err));
      setData(null);
    } finally {
      setLoading(false);
    }
  }, [jobId, enabled]);

  useEffect(() => {
    void fetchResults();
  }, [fetchResults]);

  return { data, error, loading, refetch: fetchResults };
}
