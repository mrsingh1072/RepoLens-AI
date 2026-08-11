import { apiClient } from "@/api/client";

export interface VisNode {
  id: string;
  label: string;
  kind: string;
  group: string;
  description: string;
  file_path: string;
  x: number;
  y: number;
}

export interface VisEdge {
  id: string;
  source: string;
  target: string;
  label: string;
  kind: string;
}

export interface GraphView {
  nodes: VisNode[];
  edges: VisEdge[];
}

export interface MermaidDiagrams {
  flowchart: string;
  sequence: string;
  class_diagram: string;
}

export interface DiagramBundle {
  repo_id: string;
  mermaid: MermaidDiagrams;
  system_architecture: GraphView;
  dependency_graph: GraphView;
  markdown: string;
  stats: Record<string, string | number>;
}

export async function fetchDiagrams(encodedRepoId: string): Promise<DiagramBundle> {
  const { data } = await apiClient.get<DiagramBundle>(`/diagrams/${encodedRepoId}`, {
    timeout: 60_000,
  });
  return data;
}

export async function exportMarkdown(encodedRepoId: string): Promise<string> {
  const { data } = await apiClient.get<string>(`/diagrams/${encodedRepoId}/export/markdown`, {
    timeout: 60_000,
    responseType: "text",
    transformResponse: [(v) => v],
  });
  return data;
}
