/** Tree-sitter parse result types (mirrors backend JSON output). */

export interface ParsedParameter {
  name: string;
  type: string | null;
}

export interface ParsedFunction {
  name: string;
  parameters: ParsedParameter[];
  return_type: string | null;
  start_line: number;
  end_line: number;
  docstring: string | null;
  is_method: boolean;
  class_name: string | null;
}

export interface ParsedClass {
  name: string;
  methods: ParsedFunction[];
  bases: string[];
  attributes: string[];
  start_line: number;
  end_line: number;
  docstring: string | null;
}

export interface ParsedImport {
  module: string;
  names: string[];
  is_external: boolean;
  start_line: number;
}

export interface ParsedApiEndpoint {
  route: string;
  method: string;
  handler: string;
  start_line: number;
}

export interface ParsedFileMetadata {
  complexity: string;
  lines: number;
  symbol_count: number;
}

export interface ParsedFileResult {
  file: string;
  language: string;
  classes: ParsedClass[];
  functions: ParsedFunction[];
  imports: ParsedImport[];
  api_endpoints: ParsedApiEndpoint[];
  metadata: ParsedFileMetadata;
}

export interface ParseSummary {
  chunk_count: number;
  symbol_count: number;
  api_endpoint_count: number;
  files_parsed: number;
  files_skipped: number;
}

export interface ParseResultsResponse {
  job_id: string;
  files: ParsedFileResult[];
  summary?: ParseSummary;
}
