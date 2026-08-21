import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import {
  AlertTriangle,
  BarChart3,
  Boxes,
  Copy,
  FileCode2,
  FunctionSquare,
  Layers,
  Skull,
  UploadCloud,
} from "lucide-react";
import { useNavigate } from "react-router-dom";

import { fetchRepositoryAnalytics } from "@/api/analytics";
import { AnalyticsDependencyGraph } from "@/components/analytics/AnalyticsDependencyGraph";
import { ComplexityHeatmap } from "@/components/analytics/ComplexityHeatmap";
import { ComplexityChart, LanguageChart } from "@/components/analytics/MetricCharts";
import { EmptyState } from "@/components/common/EmptyState";
import { ErrorState } from "@/components/common/ErrorState";
import { Overline } from "@/components/common/Overline";
import { PageHeader } from "@/components/common/PageHeader";
import { StatCard } from "@/components/common/StatCard";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useRepoStore } from "@/store/repoStore";
import { encodeRepoId } from "@/utils/repoId";
import { formatCompact } from "@/utils/format";
import { staggerContainer } from "@/utils/motion";
import { toApiErrorMessage } from "@/api/client";
import type { RepositoryAnalytics, SymbolRef } from "@/types/analytics";

export function AnalyticsPage() {
  const navigate = useNavigate();
  const repositories = useRepoStore((s) => s.repositories);
  const selectedId = useRepoStore((s) => s.selectedRepoId);
  const activeRepo = repositories.find((r) => r.id === selectedId) ?? repositories[0];

  const [data, setData] = useState<RepositoryAnalytics | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!activeRepo || activeRepo.status !== "indexed") {
      setData(null);
      return;
    }

    let cancelled = false;
    setLoading(true);
    setError(null);

    const repoSlug = `${activeRepo.owner}/${activeRepo.name}`;
    fetchRepositoryAnalytics(encodeRepoId(repoSlug))
      .then((analytics) => {
        if (!cancelled) setData(analytics);
      })
      .catch((err) => {
        if (!cancelled) setError(toApiErrorMessage(err));
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [activeRepo?.id, activeRepo?.owner, activeRepo?.name, activeRepo?.status]);

  const openFile = (path: string) => {
    if (!activeRepo) return;
    navigate(`/repository/${activeRepo.id}?file=${encodeURIComponent(path)}`);
  };

  if (!activeRepo) {
    return (
      <EmptyState
        overline="EMPTY · NO REPOSITORY"
        icon={<BarChart3 />}
        title="No repository selected"
        description="Upload and index a repository to unlock code analytics."
        action={
          <Button onClick={() => navigate("/upload")}>
            <UploadCloud />
            Upload repository
          </Button>
        }
      />
    );
  }

  return (
    <div className="space-y-8">
      <PageHeader
        overline={`Lab report · ${activeRepo.owner}/${activeRepo.name}`}
        title="Analytics"
        description="Complexity, dependencies, and health signals extracted from the parse."
      />

      {activeRepo.status !== "indexed" && (
        <div className="flex items-center gap-3 rounded-md border border-gold/30 bg-raised px-4 py-3 text-sm text-ink-2">
          <AlertTriangle className="h-4 w-4 shrink-0 text-gold" />
          Repository indexing must complete before analytics are available.
        </div>
      )}

      {error && (
        <ErrorState title="Analytics unavailable" description={error} onRetry={() => window.location.reload()} />
      )}

      {loading && (
        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
            {Array.from({ length: 4 }).map((_, i) => (
              <Skeleton key={i} className="h-[108px] rounded-lg" />
            ))}
          </div>
          <div className="grid gap-6 lg:grid-cols-2">
            <Skeleton className="h-[340px] rounded-lg" />
            <Skeleton className="h-[340px] rounded-lg" />
          </div>
        </div>
      )}

      {!loading && data && (
        <motion.div variants={staggerContainer(0.05)} initial="hidden" animate="show" className="space-y-8">
          <motion.div variants={staggerContainer(0.04)} className="grid grid-cols-2 gap-4 lg:grid-cols-4">
            <StatCard label="Files" value={formatCompact(data.file_count)} icon={<FileCode2 />} />
            <StatCard label="Functions" value={formatCompact(data.function_count)} icon={<FunctionSquare />} />
            <StatCard label="Classes" value={formatCompact(data.class_count)} icon={<Boxes />} />
            <StatCard label="Dependency depth" value={`${data.dependency_depth}`} icon={<Layers />} />
          </motion.div>

          <div className="grid gap-6 lg:grid-cols-2">
            <LanguageChart data={data.language_distribution} />
            <ComplexityChart data={data.complexity_distribution} />
          </div>

          <div className="grid gap-6 lg:grid-cols-2">
            <HighlightCard
              title="Most complex file"
              tone="gold"
              symbol={data.most_complex_file}
              onOpen={openFile}
            />
            <HighlightCard
              title="Largest function"
              tone="ember"
              symbol={data.largest_function}
              onOpen={openFile}
            />
          </div>

          <div className="grid gap-6 lg:grid-cols-2">
            <InsightPanel
              title="Duplicate code estimate"
              icon={<Copy className="h-4 w-4 text-ink-3" />}
              metric={data.duplicate_estimate}
              metricLabel="similar symbols"
              emptyText="No duplicate clusters detected."
            >
              {data.duplicate_clusters.map((cluster) => (
                <div key={cluster.fingerprint} className="rounded-md border border-edge bg-raised p-3">
                  <div className="flex items-center justify-between font-mono text-[11px]">
                    <span className="font-medium text-ink">{cluster.count} matches</span>
                    <span className="tnum text-ink-3">{(cluster.similarity * 100).toFixed(0)}% similar</span>
                  </div>
                  <ul className="mt-2 space-y-1 font-mono text-[11px] text-ink-2">
                    {cluster.symbols.map((symbol) => (
                      <li key={`${symbol.file_path}-${symbol.name}`} className="truncate">
                        {symbol.name} · <span className="text-ink-3">{symbol.file_path}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              ))}
            </InsightPanel>

            <InsightPanel
              title="Dead code estimate"
              icon={<Skull className="h-4 w-4 text-ink-3" />}
              metric={data.dead_code_estimate}
              metricLabel="uncalled symbols"
              emptyText="No likely dead code detected."
            >
              {data.dead_code_symbols.map((symbol) => (
                <button
                  key={`${symbol.file_path}-${symbol.name}`}
                  type="button"
                  onClick={() => openFile(symbol.file_path)}
                  className="flex w-full items-center justify-between rounded-md border border-edge bg-raised px-3 py-2 text-left font-mono text-[11px] transition-colors hover:border-edge-strong"
                >
                  <span className="truncate text-ink">{symbol.name}</span>
                  <span className="tnum ml-2 shrink-0 text-ink-3">
                    {symbol.file_path} · {symbol.lines}L
                  </span>
                </button>
              ))}
            </InsightPanel>
          </div>

          <Card className="p-5">
            <Overline className="mb-4">Complexity heatmap</Overline>
            <ComplexityHeatmap cells={data.heatmap} onSelect={openFile} />
          </Card>

          <Card className="p-5">
            <Overline className="mb-4">Import dependency graph</Overline>
            <AnalyticsDependencyGraph graph={data.dependency_graph} graphKey={data.job_id} />
          </Card>
        </motion.div>
      )}
    </div>
  );
}

function HighlightCard({
  title,
  tone,
  symbol,
  onOpen,
}: {
  title: string;
  tone: "gold" | "ember";
  symbol: SymbolRef | null;
  onOpen: (path: string) => void;
}) {
  return (
    <Card className="p-5">
      <div className="flex items-center gap-2">
        <span className={tone === "gold" ? "h-2 w-2 rounded-full bg-gold" : "h-2 w-2 rounded-full bg-ember"} />
        <Overline>{title}</Overline>
      </div>
      <div className="mt-4">
        {symbol ? (
          <button
            type="button"
            onClick={() => onOpen(symbol.file_path)}
            className="w-full rounded-md border border-edge bg-raised p-4 text-left transition-colors hover:border-ember/40 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          >
            <p className="break-all font-mono text-[13px] text-ink">{symbol.file_path}</p>
            <div className="tnum mt-3 flex flex-wrap gap-3 font-mono text-[11px] text-ink-3">
              <span>{symbol.kind}</span>
              <span>{symbol.lines} lines</span>
              {symbol.complexity_score > 0 && <span>score {symbol.complexity_score}</span>}
            </div>
          </button>
        ) : (
          <p className="text-sm text-ink-2">Not enough data.</p>
        )}
      </div>
    </Card>
  );
}

function InsightPanel({
  title,
  icon,
  metric,
  metricLabel,
  emptyText,
  children,
}: {
  title: string;
  icon: React.ReactNode;
  metric: number;
  metricLabel: string;
  emptyText: string;
  children: React.ReactNode;
}) {
  return (
    <Card className="p-5">
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-2">
          {icon}
          <Overline>{title}</Overline>
        </div>
        <div className="text-right">
          <p className="tnum font-display text-2xl font-semibold leading-none text-ink">{metric}</p>
          <p className="overline-label mt-1.5">{metricLabel}</p>
        </div>
      </div>
      <div className="mt-4 max-h-72 space-y-2 overflow-y-auto pr-1">
        {metric === 0 ? <p className="text-sm text-ink-2">{emptyText}</p> : children}
      </div>
    </Card>
  );
}
