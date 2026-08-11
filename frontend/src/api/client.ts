import axios, { AxiosError, type InternalAxiosRequestConfig } from "axios";

const baseURL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api/v1";

const MAX_RETRIES = 3;
const RETRY_BASE_MS = 400;
const RETRYABLE_STATUSES = new Set([408, 429, 500, 502, 503, 504]);

type RetryConfig = InternalAxiosRequestConfig & { __retryCount?: number };

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

/** Shared, pre-configured axios instance for all backend calls. */
export const apiClient = axios.create({
  baseURL,
  timeout: 15_000,
  headers: { "Content-Type": "application/json" },
});

apiClient.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const config = error.config as RetryConfig | undefined;
    if (!config) throw error;

    const method = (config.method ?? "get").toLowerCase();
    if (method !== "get") throw error;

    const retryCount = config.__retryCount ?? 0;
    const status = error.response?.status;
    const isNetwork = !error.response || error.code === "ERR_NETWORK";

    if (retryCount >= MAX_RETRIES) throw error;
    if (!isNetwork && status !== undefined && !RETRYABLE_STATUSES.has(status)) {
      throw error;
    }

    config.__retryCount = retryCount + 1;
    await sleep(RETRY_BASE_MS * 2 ** retryCount);
    return apiClient(config);
  },
);

/** Structured error envelope returned by the backend error middleware. */
export interface ApiErrorBody {
  error: {
    code: string;
    message: string;
    request_id?: string | null;
    details?: unknown;
  };
}

/**
 * Normalise an unknown thrown value into a readable error message, preferring
 * the backend's structured error envelope when present.
 */
export function toApiErrorMessage(error: unknown): string {
  if (error instanceof AxiosError) {
    const body = error.response?.data as ApiErrorBody | undefined;
    if (body?.error?.message) {
      return body.error.message;
    }
    if (error.code === "ERR_NETWORK" || error.message === "Network Error") {
      return `Cannot reach the API at ${baseURL}. Start the backend with: cd backend && uvicorn app.main:app --reload`;
    }
    return error.message;
  }
  if (error instanceof Error) {
    return error.message;
  }
  return "An unexpected error occurred";
}
