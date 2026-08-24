import type { FileNode, LanguageBreakdown } from "@/types";
import type { ParsedFileResult } from "@/types/parse";

/* Earth palette — luminance-separated so it survives grayscale. */
const LANGUAGE_COLORS: Record<string, string> = {
  Python: "hsl(150 26% 50%)",
  TypeScript: "hsl(215 14% 58%)",
  JavaScript: "hsl(44 85% 58%)",
  Go: "hsl(150 26% 40%)",
  Rust: "hsl(24 92% 58%)",
  Java: "hsl(10 42% 52%)",
  "C++": "hsl(38 55% 64%)",
  C: "hsl(28 8% 55%)",
  Other: "hsl(28 8% 42%)",
};

/** Build a nested file tree from flat parsed file paths. */
export function buildFileTreeFromParse(files: ParsedFileResult[]): FileNode[] {
  const root: FileNode[] = [];

  const sorted = [...files].sort((a, b) => a.file.localeCompare(b.file));
  for (const file of sorted) {
    const parts = file.file.split("/");
    let current = root;

    for (let i = 0; i < parts.length; i++) {
      const part = parts[i];
      const isFile = i === parts.length - 1;
      const id = parts.slice(0, i + 1).join("/");
      let node = current.find((n) => n.id === id);

      if (!node) {
        node = {
          id,
          name: part,
          path: id,
          type: isFile ? "file" : "dir",
          ...(isFile
            ? { language: file.language, lines: file.metadata.lines }
            : { children: [] }),
        };
        current.push(node);
      }

      if (!isFile) {
        if (!node.children) node.children = [];
        current = node.children;
      }
    }
  }

  return sortTree(root);
}

function sortTree(nodes: FileNode[]): FileNode[] {
  return nodes
    .sort((a, b) => {
      if (a.type !== b.type) return a.type === "dir" ? -1 : 1;
      return a.name.localeCompare(b.name);
    })
    .map((n) => (n.children ? { ...n, children: sortTree(n.children) } : n));
}

/** Compute language breakdown by line count across parsed files. */
export function languageBreakdownFromParse(files: ParsedFileResult[]): LanguageBreakdown[] {
  const totals: Record<string, number> = {};
  let grand = 0;
  for (const f of files) {
    const lines = f.metadata?.lines ?? 0;
    totals[f.language] = (totals[f.language] ?? 0) + lines;
    grand += lines;
  }
  if (grand === 0) return [];

  return Object.entries(totals)
    .sort((a, b) => b[1] - a[1])
    .map(([language, lines]) => ({
      language,
      percentage: Math.round((lines / grand) * 1000) / 10,
      color: LANGUAGE_COLORS[language] ?? LANGUAGE_COLORS.Other,
    }));
}

export function findParsedFile(files: ParsedFileResult[], path: string): ParsedFileResult | undefined {
  return files.find((f) => f.file === path || f.file.endsWith(`/${path}`));
}
