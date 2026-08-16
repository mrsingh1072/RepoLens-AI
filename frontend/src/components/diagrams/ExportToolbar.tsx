import { Download, FileCode, Image, Share2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  downloadSvgMarkup,
  downloadText,
  exportElementPng,
  exportElementSvg,
  renderMermaidSvg,
} from "@/components/diagrams/diagramUtils";
import type { DiagramBundle } from "@/api/diagrams";

interface ExportToolbarProps {
  bundle: DiagramBundle;
  viewportRef: React.RefObject<HTMLDivElement | null>;
  activeTab: string;
}

export function ExportToolbar({ bundle, viewportRef, activeTab }: ExportToolbarProps) {
  const slug = bundle.repo_id.replace(/\//g, "_");

  const exportMarkdown = () => downloadText(bundle.markdown, `${slug}_diagrams.md`, "text/markdown");

  const exportMermaidBundle = () => {
    const content = [
      "## Flowchart",
      "```mermaid",
      bundle.mermaid.flowchart,
      "```",
      "## Sequence",
      "```mermaid",
      bundle.mermaid.sequence,
      "```",
      "## Class",
      "```mermaid",
      bundle.mermaid.class_diagram,
      "```",
    ].join("\n\n");
    downloadText(content, `${slug}_mermaid.md`, "text/markdown");
  };

  const exportViewportPng = async () => {
    if (!viewportRef.current) return;
    await exportElementPng(viewportRef.current, `${slug}_${activeTab}.png`);
  };

  const exportViewportSvg = async () => {
    if (!viewportRef.current) return;
    await exportElementSvg(viewportRef.current, `${slug}_${activeTab}.svg`);
  };

  const exportMermaidSvg = async () => {
    const key = activeTab === "sequence" ? "sequence" : activeTab === "class" ? "class_diagram" : "flowchart";
    const source = bundle.mermaid[key as keyof typeof bundle.mermaid];
    const svg = await renderMermaidSvg(source, `export-${slug}-${key}`);
    downloadSvgMarkup(svg, `${slug}_${key}.svg`);
  };

  const isMermaidTab = activeTab === "mermaid";

  return (
    <div className="flex flex-wrap gap-2">
      <Button variant="secondary" size="sm" className="gap-1.5" onClick={exportMarkdown}>
        <FileCode className="h-3.5 w-3.5" />
        Markdown
      </Button>
      <Button variant="secondary" size="sm" className="gap-1.5" onClick={exportMermaidBundle}>
        <Share2 className="h-3.5 w-3.5" />
        Mermaid
      </Button>
      <Button variant="secondary" size="sm" className="gap-1.5" onClick={exportViewportPng}>
        <Image className="h-3.5 w-3.5" />
        PNG
      </Button>
      <Button variant="secondary" size="sm" className="gap-1.5" onClick={isMermaidTab ? exportMermaidSvg : exportViewportSvg}>
        <Download className="h-3.5 w-3.5" />
        SVG
      </Button>
    </div>
  );
}
