import { apiClient } from "@/api/client";

export interface QueryCitation {
  file_path: string;
  function_name: string | null;
  class_name: string | null;
  start_line: number;
  end_line: number;
  snippet: string;
  source: string;
  score: number;
}

export interface QueryRequest {
  repo_id: string;
  question: string;
}

export interface QueryResponse {
  repo_id: string;
  question: string;
  answer: string;
  confidence: number;
  reasoning_summary: string;
  strategy: string;
  intent_reasoning: string;
  citations: QueryCitation[];
  retrieval_stats: Record<string, string | number>;
}

export async function askRepository(body: QueryRequest): Promise<QueryResponse> {
  const { data } = await apiClient.post<QueryResponse>("/query", body, {
    timeout: 120_000,
  });
  return data;
}
