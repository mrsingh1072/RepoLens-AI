import { create } from "zustand";
import { persist } from "zustand/middleware";

import { mockRepositories } from "@/data/mock";
import type { IngestionJob } from "@/types/ingestion";
import type { Repository } from "@/types";

interface RepoState {
  repositories: Repository[];
  selectedRepoId: string | null;
  selectRepo: (id: string) => void;
  addRepository: (input: { owner: string; name: string; description?: string }) => Repository;
  upsertFromIngestion: (job: IngestionJob) => Repository;
  updateFromIngestion: (job: IngestionJob) => void;
  removeRepository: (id: string) => void;
  removeRepositories: (ids: string[]) => void;
}

function jobToRepo(job: IngestionJob, existing?: Repository): Repository {
  const meta = job.metadata;
  const fileCount =
    typeof meta.file_count === "number"
      ? meta.file_count
      : typeof meta.files_parsed === "number"
        ? meta.files_parsed
        : existing?.files ?? 0;
  const chunkCount =
    typeof meta.embeddings_indexed === "number"
      ? meta.embeddings_indexed
      : typeof meta.chunk_count === "number"
        ? meta.chunk_count
        : existing?.chunks ?? 0;
  const primaryLanguage =
    typeof meta.primary_language === "string" ? meta.primary_language : existing?.language ?? "Unknown";
  const description =
    typeof meta.description === "string" && meta.description
      ? meta.description
      : existing?.description ?? `Repository ${job.owner}/${job.name}`;

  let status: Repository["status"] = "indexing";
  const totalChunks = typeof meta.chunk_count === "number" ? meta.chunk_count : 0;
  if (job.stage === "completed") {
    const embedded = typeof meta.embeddings_indexed === "number" ? meta.embeddings_indexed : chunkCount;
    status = totalChunks > 0 && embedded < totalChunks ? "failed" : "indexed";
  } else if (job.stage === "failed") status = "failed";
  else if (job.stage === "queued") status = "queued";

  return {
    id: job.id,
    name: job.name,
    owner: job.owner,
    description,
    language: primaryLanguage,
    stars: typeof meta.stars === "number" ? meta.stars : existing?.stars ?? 0,
    forks: typeof meta.forks === "number" ? meta.forks : existing?.forks ?? 0,
    files: fileCount,
    chunks: chunkCount,
    status,
    progress: job.progress,
    updatedAt: "just now",
    ingestionError: job.error,
    semanticChunks:
      typeof meta.chunk_count === "number" ? meta.chunk_count : existing?.semanticChunks,
    embeddingsIndexed:
      typeof meta.embeddings_indexed === "number" ? meta.embeddings_indexed : existing?.embeddingsIndexed,
  };
}

export const useRepoStore = create<RepoState>()(
  persist(
    (set, get) => ({
      repositories: mockRepositories,
      selectedRepoId: mockRepositories[0]?.id ?? null,

      selectRepo: (id) => set({ selectedRepoId: id }),

      addRepository: ({ owner, name, description }) => {
        const repo: Repository = {
          id: `repo-${crypto.randomUUID().slice(0, 8)}`,
          name,
          owner,
          description: description || "Imported from GitHub. Indexing in progress…",
          language: "Unknown",
          stars: 0,
          forks: 0,
          files: 0,
          chunks: 0,
          status: "queued",
          progress: 0,
          updatedAt: "just now",
        };

        set((s) => ({ repositories: [repo, ...s.repositories], selectedRepoId: repo.id }));
        return repo;
      },

      upsertFromIngestion: (job) => {
        const existing = get().repositories.find((r) => r.id === job.id);
        const repo = jobToRepo(job, existing);
        set((s) => {
          const exists = s.repositories.some((r) => r.id === job.id);
          const repositories = exists
            ? s.repositories.map((r) => (r.id === job.id ? repo : r))
            : [repo, ...s.repositories];
          return { repositories, selectedRepoId: job.id };
        });
        return repo;
      },

      updateFromIngestion: (job) => {
        const existing = get().repositories.find((r) => r.id === job.id);
        const repo = jobToRepo(job, existing);
        set((s) => ({
          repositories: s.repositories.some((r) => r.id === job.id)
            ? s.repositories.map((r) => (r.id === job.id ? repo : r))
            : [repo, ...s.repositories],
        }));
      },

      removeRepository: (id) => {
        set((s) => {
          const repositories = s.repositories.filter((r) => r.id !== id);
          const selectedRepoId =
            s.selectedRepoId === id ? (repositories[0]?.id ?? null) : s.selectedRepoId;
          return { repositories, selectedRepoId };
        });
      },

      removeRepositories: (ids) => {
        const idSet = new Set(ids);
        set((s) => {
          const repositories = s.repositories.filter((r) => !idSet.has(r.id));
          const selectedRepoId =
            s.selectedRepoId && idSet.has(s.selectedRepoId)
              ? (repositories[0]?.id ?? null)
              : s.selectedRepoId;
          return { repositories, selectedRepoId };
        });
      },
    }),
    {
      name: "ai-swe-repositories",
      partialize: (state) => ({
        repositories: state.repositories,
        selectedRepoId: state.selectedRepoId,
      }),
    },
  ),
);
