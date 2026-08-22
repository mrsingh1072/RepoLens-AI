import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import {
  AlertTriangle,
  Database,
  FileCode2,
  FolderGit2,
  GitFork,
  MessagesSquare,
  Star,
  Workflow,
} from "lucide-react";
import { useNavigate, useParams, useSearchParams } from "react-router-dom";

import { getIngestionStatus } from "@/api/ingestion";
import { EmptyState } from "@/components/common/EmptyState";
import { ErrorState } from "@/components/common/ErrorState";
import { FileTree } from "@/components/common/FileTree";
import { Overline } from "@/components/common/Overline";
import { PageHeader } from "@/components/common/PageHeader";
import { ParsedFileDetail } from "@/components/common/ParsedFileDetail";
import { RepoStatusBadge } from "@/components/common/RepoStatusBadge";
import { StatCard } from "@/components/common/StatCard";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useParseResults } from "@/hooks/useParseResults";
import { useRepoStore } from "@/store/repoStore";
import { formatCompact } from "@/utils/format";
import {
  buildFileTreeFromParse,
  findParsedFile,
  languageBreakdownFromParse,
} from "@/utils/parseResults";
import { staggerContainer } from "@/utils/motion";

export function RepositoryOverviewPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const selectedId = useRepoStore((s) => s.selectedRepoId);
  const updateFromIngestion = useRepoStore((s) => s.updateFromIngestion);
  const repo = useRepoStore((s) => s.repositories.find((r) => r.id === (id ?? selectedId)) ?? null);
  const [selectedFile, setSelectedFile] = useState<string>();
  const [refreshing, setRefreshing] = useState(false);

  const fileFromQuery = searchParams.get("file");

  useEffect(() => {
    if (fileFromQuery) {
      setSelectedFile(fileFromQuery);
    }
  }, [fileFromQuery]);

  const canLoadParse = repo?.status === "indexed" || repo?.status === "failed";
  const { data: parseData, error, loading, refetch } = useParseResults(repo?.id ?? null, canLoadParse);

  useEffect(() => {
    if (!repo?.id) return;
    let cancelled = false;
    setRefreshing(true);
    getIngestionStatus(repo.id)
      .then((job) => {
        if (!cancelled) updateFromIngestion(job);
      })
      .catch(() => {
        // Parse data may still load even when the job record is unavailable.
      })
      .finally(() => {
        if (!cancelled) setRefreshing(false);
      });
    return () => {
      cancelled = true;
    };
  }, [repo?.id, updateFromIngestion]);

  const fileTree = parseData ? buildFileTreeFromParse(parseData.files) : [];
  const languages = parseData ? languageBreakdownFromParse(parseData.files) : [];
  const selectedParsed =
    parseData && selectedFile ? findParsedFile(parseData.files, selectedFile) : undefined;
  const summary = parseData?.summary;

  if (!repo) {
    return (
      <EmptyState
        overline="ERR · NOT FOUND"
        icon={<FolderGit2 />}
        title="Repository not found"
        description="This repository may have been removed or the link is invalid."
        action={
          <Button variant="secondary" onClick={() => navigate("/dashboard")}>
            Back to dashboard
          </Button>
        }
      />
    );
  }

  const semanticChunks = summary?.chunk_count ?? repo.semanticChunks ?? 0;
  const embeddedChunks = repo.embeddingsIndexed ?? repo.chunks ?? 0;
  const filesCount = summary?.files_parsed ?? repo.files;

  return (
    <div className="space-y-8">
      <PageHeader
        overline={`Repository · ${repo.owner}`}
        title={repo.name}
        description={repo.description}
        actions={
          <>
            <Button variant="secondary" onClick={() => navigate("/architecture")}>
              <Workflow />
              Architecture
            </Button>
            <Button onClick={() => navigate("/chat")}>
              <MessagesSquare />
              Ask questions
            </Button>
          </>
        }
      />

      <div className="flex flex-wrap items-center gap-4 font-mono text-[13px] text-ink-2">
        <RepoStatusBadge status={repo.status} />
        <span className="tnum inline-flex items-center gap-1.5">
          <Star className="h-3.5 w-3.5 text-ink-3" /> {formatCompact(repo.stars)}
        </span>
        <span className="tnum inline-flex items-center gap-1.5">
          <GitFork className="h-3.5 w-3.5 text-ink-3" /> {formatCompact(repo.forks)}
        </span>
        <span className="text-ink-3">updated {repo.updatedAt}</span>
      </div>

      {repo.status === "failed" && repo.ingestionError && (
        <div className="flex items-start gap-3 rounded-md border border-gold/30 bg-raised px-4 py-3 text-sm">
          <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-gold" />
          <div>
            <p className="font-medium text-ink">Indexing incomplete</p>
            <p className="mt-1 leading-relaxed text-ink-2">{repo.ingestionError}</p>
            {embeddedChunks > 0 && semanticChunks > embeddedChunks && (
              <p className="tnum mt-2 font-mono text-xs text-ink-3">
                {embeddedChunks} of {semanticChunks} chunks embedded — re-ingest from Upload to
                continue.
              </p>
            )}
          </div>
        </div>
      )}

      <motion.div
        variants={staggerContainer(0.05)}
        initial="hidden"
        animate="show"
        className="grid grid-cols-2 gap-4 sm:grid-cols-4"
      >
        <StatCard label="Files" value={formatCompact(filesCount)} icon={<FileCode2 />} />
        <StatCard
          label="Embedded"
          value={
            semanticChunks > 0 && embeddedChunks < semanticChunks
              ? `${formatCompact(embeddedChunks)}/${formatCompact(semanticChunks)}`
              : formatCompact(embeddedChunks || semanticChunks)
          }
          icon={<Database />}
        />
        <StatCard label="Symbols" value={formatCompact(summary?.symbol_count ?? 0)} icon={<Workflow />} />
        <StatCard
          label="API routes"
          value={formatCompact(summary?.api_endpoint_count ?? 0)}
          icon={<GitFork />}
        />
      </motion.div>

      {/* The specimen table: tree | detail. */}
      <div className="grid items-start gap-6 lg:grid-cols-[minmax(0,380px)_1fr]">
        <Card className="p-5">
          <Overline className="mb-4">File explorer</Overline>
          {repo.status === "indexing" || repo.status === "queued" ? (
            <div className="space-y-2">
              <p className="animate-breathe font-mono text-[13px] text-ember">Indexing in progress…</p>
              {Array.from({ length: 6 }).map((_, i) => (
                <Skeleton key={i} className="h-7" style={{ width: `${90 - i * 6}%` }} />
              ))}
            </div>
          ) : loading || refreshing ? (
            <div className="space-y-2">
              {Array.from({ length: 8 }).map((_, i) => (
                <Skeleton key={i} className="h-7" style={{ width: `${90 - i * 6}%` }} />
              ))}
            </div>
          ) : error ? (
            <ErrorState description={error} onRetry={refetch} />
          ) : fileTree.length === 0 ? (
            <EmptyState
              overline="EMPTY · NO PARSE DATA"
              icon={<FileCode2 />}
              title="No parse data"
              description="Re-ingest this repository to generate Tree-sitter parse results."
            />
          ) : (
            <div className="max-h-[560px] overflow-y-auto pr-1">
              <FileTree
                nodes={fileTree}
                selectedId={selectedFile}
                onSelect={(n) => setSelectedFile(n.path)}
              />
            </div>
          )}
        </Card>

        <div className="space-y-6">
          {selectedParsed ? (
            <ParsedFileDetail file={selectedParsed} />
          ) : (
            fileTree.length > 0 && (
              <Card className="flex min-h-[200px] items-center justify-center p-8 text-center">
                <div>
                  <Overline>Detail</Overline>
                  <p className="mt-2 text-sm text-ink-2">
                    Select a file to inspect its symbols, routes, and imports.
                  </p>
                </div>
              </Card>
            )
          )}

          <Card className="p-5">
            <Overline className="mb-4">Languages</Overline>
            {loading ? (
              <div className="space-y-4">
                {Array.from({ length: 4 }).map((_, i) => (
                  <div key={i} className="space-y-2">
                    <Skeleton className="h-3 w-24" />
                    <Skeleton className="h-2 w-full rounded-full" />
                  </div>
                ))}
              </div>
            ) : languages.length === 0 ? (
              <p className="text-sm text-ink-2">No language data available yet.</p>
            ) : (
              <div className="space-y-4">
                <div className="flex h-2 overflow-hidden rounded-full">
                  {languages.map((l) => (
                    <motion.div
                      key={l.language}
                      initial={{ scaleX: 0 }}
                      animate={{ scaleX: 1 }}
                      transition={{ duration: 0.6, ease: [0.22, 1, 0.36, 1] }}
                      style={{ width: `${l.percentage}%`, backgroundColor: l.color, transformOrigin: "left" }}
                    />
                  ))}
                </div>
                <div className="grid gap-2.5 sm:grid-cols-2">
                  {languages.map((l) => (
                    <div key={l.language} className="flex items-center gap-2 font-mono text-[13px]">
                      <span className="h-2 w-2 rounded-full" style={{ backgroundColor: l.color }} />
                      <span className="text-ink">{l.language}</span>
                      <span className="tnum ml-auto text-ink-3">{l.percentage}%</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </Card>
        </div>
      </div>
    </div>
  );
}
