import { useMemo } from "react";
import type { Edge, Node } from "@xyflow/react";

import { InteractiveGraph } from "@/components/diagrams/InteractiveGraph";
import type { DependencyGraph } from "@/types/analytics";

function layoutNodes(nodes: DependencyGraph["nodes"]): Node[] {
  const cols = Math.ceil(Math.sqrt(nodes.length));
  return nodes.map((node, index) => ({
    id: node.id,
    type: "diagram",
    position: { x: (index % cols) * 220, y: Math.floor(index / cols) * 120 },
    data: {
      label: node.label,
      kind: node.group,
      group: node.group,
      description: node.path,
      file_path: node.path,
      color: node.group === "external" ? "hsl(44 85% 58%)" : "hsl(24 92% 58%)",
    },
    style: {
      width: 180,
    },
  }));
}

export function AnalyticsDependencyGraph({ graph, graphKey }: { graph: DependencyGraph; graphKey: string }) {
  const nodes = useMemo(() => layoutNodes(graph.nodes), [graph.nodes]);
  const edges = useMemo<Edge[]>(
    () =>
      graph.edges.map((edge, index) => ({
        id: `e-${index}`,
        source: edge.source,
        target: edge.target,
        label: edge.label,
        animated: true,
        style: { stroke: "hsl(26 12% 26%)" },
      })),
    [graph.edges],
  );

  return (
    <div>
      <div className="mb-3 flex flex-wrap gap-2 font-mono text-[11px] text-ink-2">
        <span className="rounded-full border border-edge bg-raised px-2.5 py-1">
          max depth <strong className="tnum text-ink">{graph.max_depth}</strong>
        </span>
        <span className="rounded-full border border-edge bg-raised px-2.5 py-1">
          nodes <strong className="tnum text-ink">{graph.nodes.length}</strong>
        </span>
        <span className="inline-flex items-center gap-1.5 rounded-full border border-edge bg-raised px-2.5 py-1">
          <span className="h-1.5 w-1.5 rounded-full bg-ember" /> internal
        </span>
        <span className="inline-flex items-center gap-1.5 rounded-full border border-edge bg-raised px-2.5 py-1">
          <span className="h-1.5 w-1.5 rounded-full bg-gold" /> external
        </span>
      </div>
      <InteractiveGraph
        graphKey={graphKey}
        nodes={nodes}
        edges={edges}
        heightClass="h-[420px]"
        emptyMessage="No import dependencies detected in parse data."
      />
    </div>
  );
}
