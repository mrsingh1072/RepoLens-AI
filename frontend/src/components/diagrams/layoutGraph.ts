import type { VisEdge, VisNode } from "@/api/diagrams";

const CANVAS_W = 1200;
const CANVAS_H = 720;
const MIN_NODE_GAP_Y = 100;
const MIN_NODE_GAP_X = 220;

/** Column layout for Frontend → API → Services → DB tiers. */
export function layoutSystemGraph(nodes: VisNode[]): VisNode[] {
  if (nodes.length === 0) return nodes;

  const tierOrder = ["frontend", "presentation", "business", "data", "infrastructure"];
  const tierNodes = nodes.filter((n) => n.id.startsWith("tier_"));
  const endpointNodes = nodes.filter((n) => n.id.startsWith("ep_"));
  const dbNodes = nodes.filter((n) => n.id.startsWith("db_"));
  const otherNodes = nodes.filter(
    (n) => !n.id.startsWith("tier_") && !n.id.startsWith("ep_") && !n.id.startsWith("db_"),
  );

  const positioned = new Map<string, VisNode>();

  tierNodes.forEach((node, i) => {
    const tierKey = node.group || node.id.replace("tier_", "");
    const colIdx = tierOrder.indexOf(tierKey);
    const x = colIdx >= 0 ? 0.08 + colIdx * 0.2 : 0.08 + i * 0.2;
    positioned.set(node.id, { ...node, x, y: 0.55 });
  });

  endpointNodes.forEach((node, i) => {
    const count = endpointNodes.length;
    const y = count <= 1 ? 0.35 : 0.12 + (i / Math.max(count - 1, 1)) * 0.5;
    positioned.set(node.id, { ...node, x: 0.28, y });
  });

  dbNodes.forEach((node, i) => {
    const count = dbNodes.length;
    const y = count <= 1 ? 0.55 : 0.15 + (i / Math.max(count - 1, 1)) * 0.55;
    positioned.set(node.id, { ...node, x: 0.82, y });
  });

  otherNodes.forEach((node, i) => {
    positioned.set(node.id, { ...node, x: 0.5, y: 0.15 + i * 0.15 });
  });

  return nodes.map((n) => positioned.get(n.id) ?? n);
}

/** Grid layout grouped by module group — avoids circular overlap. */
export function layoutDependencyGraph(
  nodes: VisNode[],
  edges: VisEdge[],
  maxNodes = 48,
): { nodes: VisNode[]; truncated: boolean } {
  if (nodes.length === 0) return { nodes, truncated: false };

  const degree = new Map<string, number>();
  for (const edge of edges) {
    degree.set(edge.source, (degree.get(edge.source) ?? 0) + 1);
    degree.set(edge.target, (degree.get(edge.target) ?? 0) + 1);
  }

  const ranked = [...nodes].sort(
    (a, b) => (degree.get(b.id) ?? 0) - (degree.get(a.id) ?? 0),
  );
  const truncated = ranked.length > maxNodes;
  const selected = ranked.slice(0, maxNodes);

  const groups = new Map<string, VisNode[]>();
  for (const node of selected) {
    const group = node.group || "core";
    const list = groups.get(group) ?? [];
    list.push(node);
    groups.set(group, list);
  }

  const groupOrder = ["core", "api", "service", "util", "external"];
  const sortedGroups = [...groups.entries()].sort(
    (a, b) => groupOrder.indexOf(a[0]) - groupOrder.indexOf(b[0]),
  );

  const positioned = new Map<string, VisNode>();
  let row = 0;

  for (const [, groupNodes] of sortedGroups) {
    const cols = Math.min(4, Math.max(2, Math.ceil(Math.sqrt(groupNodes.length))));
    groupNodes.forEach((node, i) => {
      const col = i % cols;
      const groupRow = Math.floor(i / cols);
      positioned.set(node.id, {
        ...node,
        x: Math.min(0.92, 0.06 + col * 0.23),
        y: Math.min(0.92, 0.06 + (row + groupRow) * 0.13),
      });
    });
    row += Math.ceil(groupNodes.length / cols) + 1;
  }

  const laidOut = selected.map((n) => positioned.get(n.id) ?? n);

  // Drop edges referencing pruned nodes
  return { nodes: laidOut, truncated };
}

export function filterEdgesForNodes(edges: VisEdge[], nodeIds: Set<string>): VisEdge[] {
  return edges.filter((e) => nodeIds.has(e.source) && nodeIds.has(e.target));
}

export { CANVAS_H, CANVAS_W, MIN_NODE_GAP_X, MIN_NODE_GAP_Y };
