import type { HeatmapCell } from "@/types/analytics";

interface ComplexityHeatmapProps {
  cells: HeatmapCell[];
  onSelect?: (path: string) => void;
}

/*
 * Heat is literal here: cells warm from stone toward ember as complexity
 * rises — a single-hue luminance ramp that stays legible in grayscale.
 */
function intensity(cell: HeatmapCell): number {
  return Math.min(1, (cell.complexity_score * Math.log10(cell.lines + 10)) / 30);
}

export function ComplexityHeatmap({ cells, onSelect }: ComplexityHeatmapProps) {
  if (!cells.length) {
    return (
      <div className="flex h-48 items-center justify-center rounded-md border border-dashed border-edge font-mono text-[13px] text-ink-3">
        No heatmap data available.
      </div>
    );
  }

  return (
    <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5">
      {cells.map((cell) => {
        const heat = intensity(cell);
        return (
          <button
            key={cell.path}
            type="button"
            onClick={() => onSelect?.(cell.path)}
            className="group relative overflow-hidden rounded-md border p-3 text-left transition-[transform,border-color] duration-200 hover:-translate-y-0.5 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            style={{
              backgroundColor: `hsl(24 ${20 + heat * 60}% ${9 + heat * 12}%)`,
              borderColor: `hsl(24 ${20 + heat * 60}% ${16 + heat * 18}%)`,
            }}
            title={`${cell.path} · ${cell.lines} lines · ${cell.complexity_label}`}
          >
            <p className="truncate font-mono text-[11px] text-ink">{cell.path.split("/").pop()}</p>
            <p className="mt-0.5 truncate font-mono text-[10px] text-ink-3">{cell.directory}</p>
            <div className="mt-2.5 flex items-center justify-between font-mono text-[10px]">
              <span
                className="uppercase tracking-wider"
                style={{ color: heat > 0.5 ? "hsl(24 92% 66%)" : "hsl(28 6% 55%)" }}
              >
                {cell.complexity_label}
              </span>
              <span className="tnum text-ink-3">{cell.lines}L</span>
            </div>
          </button>
        );
      })}
    </div>
  );
}
