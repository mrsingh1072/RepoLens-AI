import { FileCode, FunctionSquare } from "lucide-react";

import { Overline } from "@/components/common/Overline";
import type { Citation } from "@/types";

interface CitationPanelProps {
  citations: Citation[];
  fileReferences?: string[];
  functionReferences?: string[];
  onFileClick?: (path: string, line?: number) => void;
}

/** Citations are artifacts — numbered mono chips and excavated source cards. */
export function CitationPanel({
  citations,
  fileReferences = [],
  functionReferences = [],
  onFileClick,
}: CitationPanelProps) {
  const files = fileReferences.length
    ? fileReferences
    : [...new Set(citations.map((c) => c.path))];

  return (
    <div className="w-full space-y-4">
      {files.length > 0 && (
        <div>
          <Overline className="mb-2">Files</Overline>
          <div className="flex flex-wrap gap-1.5">
            {files.map((path) => (
              <button
                key={path}
                type="button"
                onClick={() => onFileClick?.(path)}
                className="inline-flex h-7 items-center gap-1.5 rounded-sm border border-edge bg-raised px-2 font-mono text-[11px] text-ink-2 transition-colors hover:border-ember/40 hover:text-ember focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
              >
                <FileCode className="h-3 w-3" />
                {path}
              </button>
            ))}
          </div>
        </div>
      )}

      {functionReferences.length > 0 && (
        <div>
          <Overline className="mb-2">Functions</Overline>
          <div className="flex flex-wrap gap-1.5">
            {functionReferences.map((name) => (
              <span
                key={name}
                className="inline-flex h-7 items-center gap-1.5 rounded-sm border border-edge bg-raised px-2 font-mono text-[11px] text-moss"
              >
                <FunctionSquare className="h-3 w-3" />
                {name}
              </span>
            ))}
          </div>
        </div>
      )}

      {citations.length > 0 && (
        <div>
          <Overline className="mb-2">Code citations</Overline>
          <div className="space-y-2">
            {citations.map((c, i) => (
              <button
                key={`${c.path}-${i}`}
                type="button"
                onClick={() => onFileClick?.(c.path, c.startLine)}
                className="group block w-full overflow-hidden rounded-md border border-edge bg-surface text-left shadow-stratum transition-colors hover:border-ember/40 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
              >
                <div className="flex items-center gap-2 border-b border-edge bg-raised/60 px-3 py-2">
                  <span className="tnum font-mono text-[10px] text-ink-3">[{i + 1}]</span>
                  <span className="truncate font-mono text-xs text-ink-2 transition-colors group-hover:text-ember">
                    {c.path}
                  </span>
                  {c.functionName && (
                    <span className="hidden rounded-sm border border-edge bg-surface px-1.5 py-0.5 font-mono text-[10px] text-moss sm:inline">
                      {c.functionName}
                    </span>
                  )}
                  <span className="tnum ml-auto shrink-0 font-mono text-[10px] text-ink-3">
                    L{c.startLine}–{c.endLine}
                  </span>
                </div>
                <pre className="max-h-32 overflow-x-auto overflow-y-hidden px-3.5 py-2.5 font-mono text-xs leading-relaxed text-ink-2">
                  {c.snippet}
                </pre>
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
