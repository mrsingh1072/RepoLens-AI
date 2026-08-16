import { useEffect, useRef } from "react";
import {
  Background,
  Controls,
  MiniMap,
  ReactFlow,
  useEdgesState,
  useNodesState,
  type Edge,
  type Node,
  type NodeTypes,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";

import { DiagramNode } from "@/components/diagrams/DiagramNode";

const nodeTypes: NodeTypes = {
  diagram: DiagramNode,
};

interface InteractiveGraphProps {
  graphKey: string;
  nodes: Node[];
  edges: Edge[];
  exportRef?: React.RefObject<HTMLDivElement | null>;
  emptyMessage?: string;
  heightClass?: string;
}

/** The map room canvas — pan, zoom, drag; dots at 3% so the bedrock stays quiet. */
export function InteractiveGraph({
  graphKey,
  nodes: initialNodes,
  edges: initialEdges,
  exportRef,
  emptyMessage = "No graph data available for this repository.",
  heightClass = "h-[560px]",
}: InteractiveGraphProps) {
  const innerRef = useRef<HTMLDivElement>(null);
  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges);

  useEffect(() => {
    setNodes(initialNodes);
    setEdges(initialEdges);
  }, [graphKey, initialNodes, initialEdges, setNodes, setEdges]);

  useEffect(() => {
    if (exportRef && innerRef.current) {
      (exportRef as React.MutableRefObject<HTMLDivElement | null>).current = innerRef.current;
    }
  }, [exportRef, graphKey, nodes.length]);

  if (initialNodes.length === 0) {
    return (
      <div
        className={`flex ${heightClass} items-center justify-center rounded-lg border border-dashed border-edge font-mono text-[13px] text-ink-3`}
      >
        {emptyMessage}
      </div>
    );
  }

  return (
    <div
      ref={innerRef}
      className={`${heightClass} w-full overflow-hidden rounded-lg border border-edge bg-bedrock shadow-stratum`}
    >
      <ReactFlow
        key={graphKey}
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        nodeTypes={nodeTypes}
        nodesDraggable
        nodesConnectable={false}
        fitView
        fitViewOptions={{ padding: 0.25, maxZoom: 1.2 }}
        minZoom={0.05}
        maxZoom={2}
        proOptions={{ hideAttribution: true }}
      >
        <Background gap={22} size={1} color="hsl(36 20% 93% / 0.05)" />
        <Controls className="!rounded-md !border !border-edge !bg-overlay !shadow-overlay [&_button]:!border-edge [&_button]:!bg-overlay [&_button]:!text-ink-2 [&_button:hover]:!bg-raised" />
        <MiniMap
          nodeColor={(n) => (n.data as { color?: string }).color ?? "hsl(24 92% 58%)"}
          maskColor="hsl(20 14% 4.2% / 0.75)"
          className="!rounded-md !border !border-edge !bg-overlay"
        />
      </ReactFlow>
    </div>
  );
}
