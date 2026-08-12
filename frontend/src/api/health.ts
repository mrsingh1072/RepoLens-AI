import { apiClient } from "@/api/client";
import type { HealthResponse } from "@/types/health";

/** Fetch backend health/liveness metadata. */
export async function getHealth(): Promise<HealthResponse> {
  const { data } = await apiClient.get<HealthResponse>("/health");
  return data;
}
