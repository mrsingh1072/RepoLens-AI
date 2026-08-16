import type { GraphView, VisEdge, VisNode } from "@/api/diagrams";
import type { Edge, Node } from "@xyflow/react";
import {
  CANVAS_H,
  CANVAS_W,
  filterEdgesForNodes,
  layoutDependencyGraph,
  layoutSystemGraph,
} from "@/components/diagrams/layoutGraph";

/* Earth palette — kinds separated by hue AND luminance (grayscale-safe). */
const KIND_COLORS: Record<string, string> = {
  frontend: "hsl(215 14% 58%)",
  backend: "hsl(24 92% 58%)",
  service: "hsl(38 55% 64%)",
  database: "hsl(150 26% 50%)",
  util: "hsl(150 26% 40%)",
  core: "hsl(24 92% 58%)",
  file: "hsl(28 8% 55%)",
  api: "hsl(215 14% 58%)",
  external: "hsl(44 85% 58%)",
};

const GROUP_COLORS: Record<string, string> = {
  frontend: "hsl(215 14% 58%)",
  presentation: "hsl(215 14% 70%)",
  business: "hsl(38 55% 64%)",
  data: "hsl(150 26% 50%)",
  infrastructure: "hsl(150 26% 40%)",
  api: "hsl(215 14% 58%)",
  service: "hsl(38 55% 64%)",
  util: "hsl(150 26% 40%)",
  core: "hsl(24 92% 58%)",
  external: "hsl(44 85% 58%)",
};

export function visToFlowNodes(nodes: VisNode[], mode: "system" | "dependency"): Node[] {
  return nodes.map((n) => {
    const color =
      mode === "dependency"
        ? GROUP_COLORS[n.group] ?? KIND_COLORS[n.kind] ?? "hsl(24 92% 58%)"
        : KIND_COLORS[n.kind] ?? GROUP_COLORS[n.group] ?? "hsl(24 92% 58%)";
    return {
      id: n.id,
      position: {
        x: n.x * CANVAS_W,
        y: n.y * CANVAS_H,
      },
      data: {
        label: n.label,
        description: n.description,
        filePath: n.file_path,
        color,
        kind: n.kind,
      },
      type: "diagram",
    };
  });
}

export function visToFlowEdges(edges: VisEdge[]): Edge[] {
  return edges.map((e) => ({
    id: e.id,
    source: e.source,
    target: e.target,
    label: e.label,
    // Live heat rule: only active flow paths carry animated ember dashes.
    animated: e.kind === "flow" || e.kind === "cross_layer",
    style: {
      stroke:
        e.kind === "import" ? "hsl(26 12% 26%)" : "hsl(24 92% 58% / 0.6)",
    },
  }));
}

export function graphViewToFlow(view: GraphView, mode: "system" | "dependency") {
  let nodes = view.nodes;
  let edges = view.edges;
  let truncated = false;

  if (mode === "system") {
    nodes = layoutSystemGraph(nodes);
  } else {
    const laid = layoutDependencyGraph(nodes, edges);
    nodes = laid.nodes;
    truncated = laid.truncated;
    const ids = new Set(nodes.map((n) => n.id));
    edges = filterEdgesForNodes(edges, ids);
  }

  return {
    nodes: visToFlowNodes(nodes, mode),
    edges: visToFlowEdges(edges),
    truncated,
  };
}

export function downloadText(content: string, filename: string, mime = "text/plain") {
  const blob = new Blob([content], { type: mime });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  anchor.click();
  URL.revokeObjectURL(url);
}

export async function exportElementPng(element: HTMLElement, filename: string) {
  const { toPng } = await import("html-to-image");
  const dataUrl = await toPng(element, {
    pixelRatio: 2,
    backgroundColor: "#0d0b09",
    cacheBust: true,
  });
  const anchor = document.createElement("a");
  anchor.href = dataUrl;
  anchor.download = filename;
  anchor.click();
}

export async function exportElementSvg(element: HTMLElement, filename: string) {
  const { toSvg } = await import("html-to-image");
  const dataUrl = await toSvg(element, {
    backgroundColor: "#0d0b09",
    cacheBust: true,
  });
  const anchor = document.createElement("a");
  anchor.href = dataUrl;
  anchor.download = filename;
  anchor.click();
}

export function cleanupMermaidArtifacts() {
  const markers = ["Syntax error in text", "mermaid version"];
  document.querySelectorAll("body > div, body > svg, [id^='dmermaid-']").forEach((el) => {
    const text = el.textContent ?? "";
    if (markers.some((m) => text.includes(m))) {
      el.remove();
    }
  });
}

export async function renderMermaidSvg(source: string, id: string): Promise<string> {
  const mermaid = (await import("mermaid")).default;
  mermaid.initialize({
    startOnLoad: false,
    theme: "base",
    securityLevel: "loose",
    suppressErrorRendering: true,
    themeVariables: {
      darkMode: true,
      background: "#0d0b09",
      primaryColor: "#1a1613",
      primaryTextColor: "#f0ebe3",
      primaryBorderColor: "#2b2620",
      lineColor: "#6b6257",
      secondaryColor: "#211c17",
      tertiaryColor: "#14100d",
      fontFamily: '"IBM Plex Mono", monospace',
      fontSize: "13px",
    },
  });

  const sanitized = source.trim() || "flowchart TB\n  empty[No diagram data]";

  try {
    const { svg } = await mermaid.render(id, sanitized);
    cleanupMermaidArtifacts();
    return svg;
  } catch (err) {
    cleanupMermaidArtifacts();
    throw err;
  }
}

export function downloadSvgMarkup(svg: string, filename: string) {
  downloadText(svg, filename, "image/svg+xml");
}
