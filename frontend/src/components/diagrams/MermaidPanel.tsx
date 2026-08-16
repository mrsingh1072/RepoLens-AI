import { useEffect, useId, useRef, useState } from "react";

import { cleanupMermaidArtifacts, renderMermaidSvg } from "@/components/diagrams/diagramUtils";
import { Overline } from "@/components/common/Overline";
import { cn } from "@/utils/cn";

interface MermaidPanelProps {
  title: string;
  source: string;
  exportRef?: React.RefObject<HTMLDivElement | null>;
}

export function MermaidPanel({ title, source, exportRef }: MermaidPanelProps) {
  const uid = useId().replace(/:/g, "");
  const containerRef = useRef<HTMLDivElement>(null);
  const [svg, setSvg] = useState("");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setError(null);
    renderMermaidSvg(source, `mmd-${uid}-${title.replace(/\s+/g, "-")}`)
      .then((markup) => {
        if (!cancelled) setSvg(markup);
      })
      .catch((err) => {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "Failed to render diagram");
          setSvg("");
        }
      });
    return () => {
      cancelled = true;
      cleanupMermaidArtifacts();
    };
  }, [source, title, uid]);

  useEffect(() => {
    if (exportRef && containerRef.current) {
      (exportRef as React.MutableRefObject<HTMLDivElement | null>).current = containerRef.current;
    }
  }, [exportRef, svg]);

  return (
    <div className="space-y-2.5">
      <Overline>{title}</Overline>
      <div
        ref={containerRef}
        className={cn(
          "overflow-auto rounded-lg border border-edge bg-surface p-4 shadow-stratum",
          "min-h-[280px]",
        )}
      >
        {error ? (
          <div className="space-y-2">
            <p className="font-mono text-xs text-rust">{error}</p>
            <pre className="overflow-x-auto font-mono text-xs text-ink-3">{source}</pre>
          </div>
        ) : svg ? (
          <div className="flex justify-center [&_svg]:max-w-full" dangerouslySetInnerHTML={{ __html: svg }} />
        ) : (
          <p className="animate-breathe font-mono text-xs text-ember">Rendering diagram…</p>
        )}
      </div>
    </div>
  );
}
