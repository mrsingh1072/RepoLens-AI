import { apiClient } from "@/api/client";
import type { RepositoryAnalytics } from "@/types/analytics";

export async function fetchRepositoryAnalytics(encodedRepoId: string): Promise<RepositoryAnalytics> {
  const { data } = await apiClient.get<RepositoryAnalytics>(`/analytics/${encodedRepoId}`, {
    timeout: 60_000,
  });
  return data;
}
