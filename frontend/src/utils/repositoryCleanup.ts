import { deleteIngestionJob } from "@/api/ingestion";
import { toApiErrorMessage } from "@/api/client";
import type { Repository } from "@/types";

export interface BulkRemoveResult {
  removed: Repository[];
  failed: Array<{ repo: Repository; error: string }>;
}

/** Delete backend artifacts and return which repos succeeded or failed. */
export async function removeRepositoriesFromBackend(repos: Repository[]): Promise<BulkRemoveResult> {
  const removed: Repository[] = [];
  const failed: BulkRemoveResult["failed"] = [];

  await Promise.all(
    repos.map(async (repo) => {
      try {
        if (repo.id.startsWith("job-")) {
          await deleteIngestionJob(repo.id);
        }
        removed.push(repo);
      } catch (error) {
        failed.push({ repo, error: toApiErrorMessage(error) });
      }
    }),
  );

  return { removed, failed };
}
