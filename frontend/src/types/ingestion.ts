/** Ingestion pipeline types (mirrors backend schemas). */

export type IngestionStage =
  | "queued"
  | "validating"
  | "cloning"
  | "parsing"
  | "graphing"
  | "indexing"
  | "embedding"
  | "completed"
  | "failed";

export interface IngestionJob {
  id: string;
  source: "github" | "zip";
  owner: string;
  name: string;
  stage: IngestionStage;
  progress: number;
  message: string;
  error: string | null;
  metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface IngestionStartResponse {
  job_id: string;
  message: string;
}

export interface GitHubIngestionRequest {
  url: string;
  token?: string;
}
