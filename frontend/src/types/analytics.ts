export interface SymbolRef {
  name: string;
  file_path: string;
  start_line: number;
  end_line: number;
  kind: string;
  lines: number;
  complexity_score: number;
}

export interface DuplicateCluster {
  fingerprint: string;
  count: number;
  similarity: number;
  symbols: SymbolRef[];
}

export interface LanguageSlice {
  language: string;
  files: number;
  lines: number;
  percentage: number;
}

export interface ComplexitySlice {
  level: string;
  count: number;
}

export interface HeatmapCell {
  path: string;
  directory: string;
  language: string;
  lines: number;
  complexity_score: number;
  symbol_count: number;
  complexity_label: string;
}

export interface DependencyNode {
  id: string;
  label: string;
  path: string;
  group: string;
}

export interface DependencyEdge {
  source: string;
  target: string;
  label: string;
}

export interface DependencyGraph {
  nodes: DependencyNode[];
  edges: DependencyEdge[];
  max_depth: number;
}

export interface RepositoryAnalytics {
  repo_id: string;
  job_id: string;
  file_count: number;
  function_count: number;
  class_count: number;
  dependency_depth: number;
  most_complex_file: SymbolRef | null;
  largest_function: SymbolRef | null;
  duplicate_clusters: DuplicateCluster[];
  duplicate_estimate: number;
  dead_code_symbols: SymbolRef[];
  dead_code_estimate: number;
  language_distribution: LanguageSlice[];
  complexity_distribution: ComplexitySlice[];
  heatmap: HeatmapCell[];
  dependency_graph: DependencyGraph;
  summary: Record<string, number | string | null>;
}
