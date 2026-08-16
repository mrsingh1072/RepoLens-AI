import { memo } from "react";
import { Handle, Position, type NodeProps } from "@xyflow/react";

interface DiagramNodeData {
  label: string;
  description?: string;
  filePath?: string;
  color: string;
  kind?: string;
}

/*
 * Graph nodes are miniature strata: warm graphite card, kind-colored dot,
 * mono metadata. Selection raises the node with an ember edge.
 */
function DiagramNodeComponent({ data, selected }: NodeProps) {
  const d = data as unknown as DiagramNodeData;
  return (
    <div
      className="min-w-[140px] max-w-[220px] rounded-md border bg-surface px-3 py-2.5 shadow-stratum transition-shadow"
      style={{
        borderColor: selected ? "hsl(24 92% 58%)" : "hsl(26 10% 15.5%)",
        boxShadow: selected
          ? "0 8px 32px -8px hsl(24 92% 58% / 0.35)"
          : undefined,
      }}
    >
      <Handle type="target" position={Position.Left} className="!h-1.5 !w-1.5 !border-0 !bg-[hsl(28_6%_45%)]" />
      <div className="flex items-center gap-2">
        <span className="h-2 w-2 shrink-0 rounded-full" style={{ backgroundColor: d.color }} />
        <span className="truncate text-[13px] font-medium text-ink">{d.label}</span>
      </div>
      {d.kind && (
        <p className="mt-1 font-mono text-[9px] uppercase tracking-[0.14em] text-ink-3">{d.kind}</p>
      )}
      {d.description && (
        <p className="mt-1 line-clamp-2 text-[11px] leading-snug text-ink-2">{d.description}</p>
      )}
      {d.filePath && (
        <p className="mt-1 truncate font-mono text-[10px] text-ink-3">{d.filePath}</p>
      )}
      <Handle type="source" position={Position.Right} className="!h-1.5 !w-1.5 !border-0 !bg-[hsl(28_6%_45%)]" />
    </div>
  );
}

export const DiagramNode = memo(DiagramNodeComponent);
