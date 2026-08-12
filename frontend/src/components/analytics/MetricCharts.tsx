import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { Card } from "@/components/ui/card";
import { Overline } from "@/components/common/Overline";
import { CHART_THEME, COMPLEXITY_COLORS, languageColor } from "@/components/analytics/chartTheme";
import type { ComplexitySlice, LanguageSlice } from "@/types/analytics";

/* Lab-report charts: hairline grid, no axis lines, mono labels, warm tooltip. */

function ChartTooltip({
  active,
  payload,
  label,
}: {
  active?: boolean;
  payload?: Array<{ value: number; name: string; payload?: LanguageSlice }>;
  label?: string;
}) {
  if (!active || !payload?.length) return null;
  const row = payload[0];
  return (
    <div
      className="rounded-md border px-3 py-2 font-mono text-xs shadow-overlay"
      style={{ background: CHART_THEME.tooltipBg, borderColor: CHART_THEME.tooltipBorder }}
    >
      <p className="font-medium text-ink">{label ?? row.name}</p>
      <p className="tnum mt-0.5 text-ink-2">{row.value}</p>
    </div>
  );
}

export function LanguageChart({ data }: { data: LanguageSlice[] }) {
  return (
    <Card className="overflow-hidden p-5">
      <Overline>Language distribution</Overline>
      <div className="mt-2 h-[260px]">
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie
              data={data}
              dataKey="lines"
              nameKey="language"
              innerRadius={62}
              outerRadius={92}
              paddingAngle={2}
              stroke="hsl(22 12% 6.8%)"
              strokeWidth={2}
              animationDuration={700}
              animationEasing="ease-out"
            >
              {data.map((entry) => (
                <Cell key={entry.language} fill={languageColor(entry.language)} />
              ))}
            </Pie>
            <Tooltip
              content={({ active, payload }) => {
                if (!active || !payload?.length) return null;
                const row = payload[0].payload as LanguageSlice;
                return (
                  <div
                    className="rounded-md border px-3 py-2 font-mono text-xs shadow-overlay"
                    style={{ background: CHART_THEME.tooltipBg, borderColor: CHART_THEME.tooltipBorder }}
                  >
                    <p className="font-medium capitalize text-ink">{row.language}</p>
                    <p className="tnum mt-0.5 text-ink-2">
                      {row.lines.toLocaleString()} lines · {row.percentage}%
                    </p>
                  </div>
                );
              }}
            />
          </PieChart>
        </ResponsiveContainer>
      </div>
      <div className="mt-3 flex flex-wrap justify-center gap-x-4 gap-y-1.5">
        {data.map((row) => (
          <div key={row.language} className="flex items-center gap-1.5 font-mono text-[11px] text-ink-2">
            <span className="h-2 w-2 rounded-full" style={{ backgroundColor: languageColor(row.language) }} />
            <span className="capitalize">{row.language}</span>
            <span className="tnum text-ink-3">{row.percentage}%</span>
          </div>
        ))}
      </div>
    </Card>
  );
}

export function ComplexityChart({ data }: { data: ComplexitySlice[] }) {
  return (
    <Card className="overflow-hidden p-5">
      <Overline>Complexity distribution</Overline>
      <div className="mt-2 h-[290px]">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} margin={{ top: 12, right: 8, left: -16, bottom: 0 }}>
            <CartesianGrid strokeDasharray="0" stroke={CHART_THEME.grid} vertical={false} />
            <XAxis
              dataKey="level"
              tick={{ fill: CHART_THEME.axis, fontSize: 11, fontFamily: '"IBM Plex Mono", monospace' }}
              axisLine={false}
              tickLine={false}
            />
            <YAxis
              tick={{ fill: CHART_THEME.axis, fontSize: 11, fontFamily: '"IBM Plex Mono", monospace' }}
              axisLine={false}
              tickLine={false}
            />
            <Tooltip content={<ChartTooltip />} cursor={{ fill: "hsl(24 10% 9.5% / 0.6)" }} />
            <Bar dataKey="count" radius={[6, 6, 0, 0]} animationDuration={700} animationEasing="ease-out">
              {data.map((entry) => (
                <Cell
                  key={entry.level}
                  fill={COMPLEXITY_COLORS[entry.level as keyof typeof COMPLEXITY_COLORS] ?? "hsl(28 8% 42%)"}
                />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </Card>
  );
}
