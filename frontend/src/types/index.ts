/** Domain types shared across the UI. */

export type RepoStatus = "indexed" | "indexing" | "queued" | "failed";

export interface Repository {
  id: string;
  name: string;
  owner: string;
  description: string;
  language: string;
  stars: number;
  forks: number;
  files: number;
  chunks: number;
  status: RepoStatus;
  /** Indexing progress 0-100 (only meaningful while status === "indexing"). */
  progress: number;
  updatedAt: string;
  ingestionError?: string | null;
  semanticChunks?: number;
  embeddingsIndexed?: number;
}

export interface LanguageBreakdown {
  language: string;
  percentage: number;
  color: string;
}

export interface FileNode {
  id: string;
  name: string;
  path: string;
  type: "file" | "dir";
  language?: string;
  lines?: number;
  children?: FileNode[];
}

export interface Citation {
  path: string;
  startLine: number;
  endLine: number;
  snippet: string;
  functionName?: string | null;
  source?: string;
  score?: number;
}

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  citations?: Citation[];
  confidence?: number;
  reasoningSummary?: string;
  reasoningSteps?: string[];
  plan?: string[];
  toolsUsed?: string[];
  fileReferences?: string[];
  functionReferences?: string[];
  followUpSuggestions?: string[];
  isStreaming?: boolean;
  statusLabel?: string;
  strategy?: string;
  createdAt: string;
}

export interface ArchitectureNode {
  id: string;
  label: string;
  kind: "frontend" | "backend" | "service" | "database" | "external";
  description: string;
  x: number;
  y: number;
}

export interface ArchitectureEdge {
  from: string;
  to: string;
  label?: string;
}

export interface DependencyNode {
  id: string;
  label: string;
  group: "core" | "api" | "service" | "util" | "external";
  size: number;
}

export interface DependencyEdge {
  source: string;
  target: string;
}

export interface ActivityItem {
  id: string;
  type: "index" | "query" | "upload" | "error";
  title: string;
  detail: string;
  time: string;
}
