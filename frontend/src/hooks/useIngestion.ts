import { useCallback, useEffect, useRef, useState } from "react";

import { getIngestionStatus, subscribeIngestionEvents } from "@/api/ingestion";
import type { IngestionJob } from "@/types/ingestion";

interface Options {
  /** Poll every N ms when SSE is unavailable. */
  pollIntervalMs?: number;
  /** How many consecutive poll errors before giving up. */
  maxPollErrors?: number;
}

export function useIngestionProgress(jobId: string | null, options: Options = {}) {
  const { pollIntervalMs = 2000, maxPollErrors = 10 } = options;
  const [job, setJob] = useState<IngestionJob | null>(null);
  const [error, setError] = useState<string | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const pollErrorCount = useRef(0);

  const isActive = job?.stage !== "completed" && job?.stage !== "failed";
  const isComplete = job?.stage === "completed";
  const isFailed = job?.stage === "failed";

  const stopPolling = useCallback(() => {
    if (pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
    pollErrorCount.current = 0;
  }, []);

  useEffect(() => {
    if (!jobId) {
      setJob(null);
      setError(null);
      return;
    }

    setError(null);
    pollErrorCount.current = 0;
    let cancelled = false;
    let unsubscribe: (() => void) | null = null;

    const handleUpdate = (update: IngestionJob) => {
      if (!cancelled) {
        setJob(update);
        pollErrorCount.current = 0; // reset error count on successful update
      }
    };

    // Try SSE first; fall back to polling on error.
    unsubscribe = subscribeIngestionEvents(
      jobId,
      handleUpdate,
      () => {
        if (cancelled || pollRef.current) return;
        pollRef.current = setInterval(async () => {
          try {
            const status = await getIngestionStatus(jobId);
            if (!cancelled) {
              setJob(status);
              pollErrorCount.current = 0;
            }
            if (status.stage === "completed" || status.stage === "failed") {
              stopPolling();
            }
          } catch {
            pollErrorCount.current += 1;
            // Only give up after maxPollErrors consecutive failures
            if (pollErrorCount.current >= maxPollErrors) {
              if (!cancelled) setError("Lost connection to ingestion service.");
              stopPolling();
            }
            // Otherwise silently retry — backend may be briefly restarting
          }
        }, pollIntervalMs);
      },
    );

    return () => {
      cancelled = true;
      unsubscribe?.();
      stopPolling();
    };
  }, [jobId, pollIntervalMs, maxPollErrors, stopPolling]);

  return { job, error, isActive, isComplete, isFailed };
}
