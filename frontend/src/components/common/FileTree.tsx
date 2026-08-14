import { useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { ChevronRight, File, FileCode, Folder, FolderOpen } from "lucide-react";

import { cn } from "@/utils/cn";
import { snap } from "@/utils/motion";
import type { FileNode } from "@/types";

/*
 * File tree: hairline indent guides, snapping chevrons, ember left rail
 * on the active file, mono line-counts on hover.
 */

interface FileTreeProps {
  nodes: FileNode[];
  onSelect?: (node: FileNode) => void;
  selectedId?: string;
}

export function FileTree({ nodes, onSelect, selectedId }: FileTreeProps) {
  return (
    <div className="font-mono text-[13px]">
      {nodes.map((node) => (
        <TreeRow key={node.id} node={node} depth={0} onSelect={onSelect} selectedId={selectedId} />
      ))}
    </div>
  );
}

function countFiles(node: FileNode): number {
  if (node.type === "file") return 1;
  return (node.children ?? []).reduce((acc, child) => acc + countFiles(child), 0);
}

function TreeRow({
  node,
  depth,
  onSelect,
  selectedId,
}: {
  node: FileNode;
  depth: number;
  onSelect?: (node: FileNode) => void;
  selectedId?: string;
}) {
  const [open, setOpen] = useState(depth < 1);
  const isDir = node.type === "dir";
  const isSelected = node.id === selectedId || node.path === selectedId;

  return (
    <div className={cn(depth > 0 && "border-l border-edge")} style={depth > 0 ? { marginLeft: 11 } : undefined}>
      <button
        onClick={() => (isDir ? setOpen((o) => !o) : onSelect?.(node))}
        className={cn(
          "group relative flex w-full items-center gap-1.5 rounded-sm py-1.5 pl-2 pr-2 text-left transition-colors hover:bg-raised",
          isSelected && "bg-raised text-ink",
          !isSelected && "text-ink-2",
        )}
      >
        {isSelected && !isDir && (
          <span className="absolute inset-y-1 left-0 w-0.5 rounded-full bg-ember" aria-hidden />
        )}
        {isDir ? (
          <>
            <motion.span animate={{ rotate: open ? 90 : 0 }} transition={snap} className="flex">
              <ChevronRight className="h-3.5 w-3.5 shrink-0 text-ink-3" />
            </motion.span>
            {open ? (
              <FolderOpen className="h-4 w-4 shrink-0 text-ink-3" />
            ) : (
              <Folder className="h-4 w-4 shrink-0 text-ink-3" />
            )}
          </>
        ) : (
          <>
            <span className="w-3.5" />
            {node.language ? (
              <FileCode className="h-4 w-4 shrink-0 text-ink-3" />
            ) : (
              <File className="h-4 w-4 shrink-0 text-ink-3" />
            )}
          </>
        )}
        <span className="truncate">{node.name}</span>
        {isDir ? (
          <span className="ml-auto text-[11px] text-ink-3">{countFiles(node)}</span>
        ) : node.lines != null ? (
          <span className="ml-auto text-[11px] text-ink-3 opacity-0 transition-opacity group-hover:opacity-100">
            {node.lines}L
          </span>
        ) : null}
      </button>

      <AnimatePresence initial={false}>
        {isDir && open && node.children && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.18, ease: "easeOut" }}
            className="overflow-hidden"
          >
            {node.children.map((child) => (
              <TreeRow key={child.id} node={child} depth={depth + 1} onSelect={onSelect} selectedId={selectedId} />
            ))}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
