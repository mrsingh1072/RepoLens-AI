import { apiClient } from "@/api/client";
import type { GitHubIngestionRequest, IngestionJob, IngestionStartResponse } from "@/types/ingestion";
import type { ParseResultsResponse } from "@/types/parse";

const baseURL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api/v1";

export async function startGitHubIngestion(
  body: GitHubIngestionRequest,
): Promise<IngestionStartResponse> {
  const { data } = await apiClient.post<IngestionStartResponse>("/ingestion/github", body);
  return data;
}

export async function startZipIngestion(file: File, name: string, owner = "local"): Promise<IngestionStartResponse> {
  const form = new FormData();
  form.append("file", file);
  form.append("name", name);
  form.append("owner", owner);

  const { data } = await apiClient.post<IngestionStartResponse>("/ingestion/upload", form, {
    headers: { "Content-Type": "multipart/form-data" },
    timeout: 120_000,
  });
  return data;
}

export async function getIngestionStatus(jobId: string): Promise<IngestionJob> {
  const { data } = await apiClient.get<IngestionJob>(`/ingestion/${jobId}`);
  return data;
}

export async function deleteIngestionJob(jobId: string): Promise<void> {
  await apiClient.delete(`/ingestion/${jobId}`, { timeout: 60_000 });
}

export async function getParseResults(jobId: string): Promise<ParseResultsResponse> {
  const { data } = await apiClient.get<ParseResultsResponse>(`/ingestion/${jobId}/parse`);
  return data;
}

/** Open an SSE stream for real-time ingestion progress. */
export function subscribeIngestionEvents(
  jobId: string,
  onEvent: (job: IngestionJob) => void,
  onError?: (error: Event) => void,
): () => void {
  const url = `${baseURL}/ingestion/${jobId}/events`;
  let source: EventSource | null = null;
  let closed = false;
  let retryCount = 0;
  const maxRetries = 5;

  function connect() {
    if (closed) return;
    source = new EventSource(url);

    source.onmessage = (event) => {
      retryCount = 0; // reset on successful message
      try {
        const job = JSON.parse(event.data) as IngestionJob;
        onEvent(job);
        if (job.stage === "completed" || job.stage === "failed") {
          source?.close();
        }
      } catch {
        // Ignore malformed events.
      }
    };

    source.onerror = () => {
      source?.close();
      source = null;
      if (closed) return;

      if (retryCount < maxRetries) {
        // Exponential backoff: 1s, 2s, 4s, 8s, 16s
        const delay = Math.min(1000 * 2 ** retryCount, 16000);
        retryCount += 1;
        setTimeout(connect, delay);
      } else {
        // Exhausted retries — fall back to polling
        onError?.(new Event("error"));
      }
    };
  }

  connect();

  return () => {
    closed = true;
    source?.close();
  };
}
