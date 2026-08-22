import { useCallback, useEffect, useRef, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  ArrowRight,
  CheckCircle2,
  FileArchive,
  Github,
  KeyRound,
  Loader2,
  Lock,
} from "lucide-react";
import { toast } from "sonner";
import { useNavigate } from "react-router-dom";

import { startGitHubIngestion, startZipIngestion } from "@/api/ingestion";
import { toApiErrorMessage } from "@/api/client";
import { BlueprintCorners } from "@/components/common/BlueprintCorners";
import { IngestionProgress } from "@/components/common/IngestionProgress";
import { Overline } from "@/components/common/Overline";
import { PageHeader } from "@/components/common/PageHeader";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { useIngestionProgress } from "@/hooks/useIngestion";
import { useRepoStore } from "@/store/repoStore";
import { cn } from "@/utils/cn";
import { fadeInUp, staggerContainer } from "@/utils/motion";

const GITHUB_URL = /^(?:https?:\/\/github\.com\/)?([\w.-]+)\/([\w.-]+?)(?:\.git)?\/?$/i;
const MAX_ZIP_MB = 200;

type InputMode = "github" | "zip";

export function UploadRepositoryPage() {
  const navigate = useNavigate();
  const upsertFromIngestion = useRepoStore((s) => s.upsertFromIngestion);
  const updateFromIngestion = useRepoStore((s) => s.updateFromIngestion);

  const [mode, setMode] = useState<InputMode>("github");
  const [value, setValue] = useState("");
  const [token, setToken] = useState("");
  const [showToken, setShowToken] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [dragActive, setDragActive] = useState(false);
  const [activeJobId, setActiveJobId] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const { job, isComplete, isFailed } = useIngestionProgress(activeJobId);

  useEffect(() => {
    if (job) updateFromIngestion(job);
  }, [job, updateFromIngestion]);

  const startGithub = useCallback(async () => {
    const match = value.trim().match(GITHUB_URL);
    if (!match) {
      setError("Enter a valid GitHub URL, e.g. github.com/owner/repo");
      return;
    }
    setError(null);
    setSubmitting(true);

    try {
      const { job_id } = await startGitHubIngestion({
        url: value.trim(),
        token: token.trim() || undefined,
      });
      const [, owner, name] = match;
      upsertFromIngestion({
        id: job_id,
        source: "github",
        owner,
        name,
        stage: "queued",
        progress: 0,
        message: "Starting ingestion…",
        error: null,
        metadata: {},
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      });
      setActiveJobId(job_id);
      toast.success("Ingestion started", { description: `${owner}/${name} is being indexed.` });
    } catch (err) {
      setError(toApiErrorMessage(err));
    } finally {
      setSubmitting(false);
    }
  }, [value, token, upsertFromIngestion]);

  const startZip = useCallback(
    async (file: File) => {
      if (!file.name.toLowerCase().endsWith(".zip")) {
        setError("Only .zip archives are supported.");
        return;
      }
      if (file.size > MAX_ZIP_MB * 1024 * 1024) {
        setError(`Archive must be under ${MAX_ZIP_MB} MB.`);
        return;
      }

      const baseName = file.name.replace(/\.zip$/i, "");
      setError(null);
      setSubmitting(true);

      try {
        const { job_id } = await startZipIngestion(file, baseName);
        upsertFromIngestion({
          id: job_id,
          source: "zip",
          owner: "local",
          name: baseName,
          stage: "queued",
          progress: 0,
          message: "Extracting archive…",
          error: null,
          metadata: {},
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
        });
        setActiveJobId(job_id);
        toast.success("Archive uploaded", { description: `${baseName} is being indexed.` });
      } catch (err) {
        setError(toApiErrorMessage(err));
      } finally {
        setSubmitting(false);
      }
    },
    [upsertFromIngestion],
  );

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragActive(false);
    const file = e.dataTransfer.files[0];
    if (file) {
      setMode("zip");
      void startZip(file);
    }
  };

  const onComplete = () => {
    if (job) navigate(`/repository/${job.id}`);
  };

  return (
    <div className="mx-auto max-w-3xl space-y-8">
      <PageHeader
        overline="Intake"
        title="Add a repository"
        description="Connect a GitHub repository or upload a ZIP archive. RepoLens AI will excavate it — parse, graph, index, embed."
      />

      <motion.div variants={staggerContainer(0.07)} initial="hidden" animate="show" className="space-y-6">
        {/* The machine at work. */}
        <AnimatePresence>
          {job && (
            <motion.div
              variants={fadeInUp}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0 }}
            >
              <IngestionProgress job={job} />
              {isComplete && (
                <div className="mt-4 flex justify-end">
                  <Button onClick={onComplete}>
                    <CheckCircle2 />
                    View repository
                  </Button>
                </div>
              )}
              {isFailed && (
                <div className="mt-4 flex justify-end">
                  <Button variant="secondary" onClick={() => setActiveJobId(null)}>
                    Try another source
                  </Button>
                </div>
              )}
            </motion.div>
          )}
        </AnimatePresence>

        {/* GitHub URL intake */}
        <motion.div variants={fadeInUp}>
          <Card className="space-y-4 p-6">
            <div className="flex items-center gap-2.5">
              <Github className="h-4 w-4 text-ink-3" />
              <label htmlFor="repo-url">
                <Overline>Source · GitHub</Overline>
              </label>
            </div>
            <div className="flex flex-col gap-2 sm:flex-row">
              <Input
                id="repo-url"
                placeholder="github.com/owner/repository"
                value={value}
                onChange={(e) => {
                  setValue(e.target.value);
                  setMode("github");
                  if (error) setError(null);
                }}
                onKeyDown={(e) => e.key === "Enter" && !submitting && startGithub()}
                className={cn(
                  "flex-1 font-mono text-[13px]",
                  error && mode === "github" && "border-rust/50 focus-visible:ring-rust/40",
                )}
                aria-invalid={!!error && mode === "github"}
                disabled={submitting || !!activeJobId}
              />
              <Button
                onClick={() => void startGithub()}
                disabled={submitting || !!activeJobId}
                className="sm:w-36"
              >
                {submitting && mode === "github" ? (
                  <>
                    <Loader2 className="animate-spin" />
                    Connecting…
                  </>
                ) : (
                  <>
                    Index repo
                    <ArrowRight />
                  </>
                )}
              </Button>
            </div>

            {/* GitHub token (private repos) */}
            <div>
              <button
                type="button"
                onClick={() => setShowToken((v) => !v)}
                className="inline-flex items-center gap-1.5 text-xs text-ink-3 transition-colors hover:text-ink-2"
              >
                <KeyRound className="h-3.5 w-3.5" />
                {showToken ? "Hide" : "Add"} GitHub token for private repos
              </button>
              {showToken && (
                <div className="relative mt-2">
                  <Lock className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-ink-3" />
                  <Input
                    type="password"
                    placeholder="ghp_…"
                    value={token}
                    onChange={(e) => setToken(e.target.value)}
                    className="pl-9 font-mono text-[13px]"
                    disabled={submitting || !!activeJobId}
                    autoComplete="off"
                  />
                </div>
              )}
            </div>

            {error && mode === "github" ? (
              <p className="font-mono text-[13px] text-rust">{error}</p>
            ) : (
              <p className="text-xs leading-relaxed text-ink-3">
                Public repos work without a token. Private repos require a personal access token
                with <code className="rounded-sm bg-raised px-1 font-mono text-ink-2">repo</code>{" "}
                scope.
              </p>
            )}
          </Card>
        </motion.div>

        {/* Dropzone */}
        <motion.div variants={fadeInUp}>
          <input
            ref={fileInputRef}
            type="file"
            accept=".zip"
            className="hidden"
            onChange={(e) => {
              const file = e.target.files?.[0];
              if (file) void startZip(file);
              e.target.value = "";
            }}
          />
          <div
            onDragOver={(e) => {
              e.preventDefault();
              setDragActive(true);
            }}
            onDragLeave={() => setDragActive(false)}
            onDrop={handleDrop}
            onClick={() => !submitting && !activeJobId && fileInputRef.current?.click()}
            role="button"
            tabIndex={0}
            onKeyDown={(e) => e.key === "Enter" && fileInputRef.current?.click()}
            className={cn(
              "relative flex cursor-pointer flex-col items-center justify-center rounded-lg border border-dashed px-6 py-12 text-center transition-colors",
              dragActive ? "border-ember/60 bg-ember/[0.04]" : "border-edge hover:border-edge-strong",
              (submitting || activeJobId) && "pointer-events-none opacity-50",
            )}
          >
            <BlueprintCorners />
            <div className="flex h-12 w-12 items-center justify-center rounded-lg border border-edge bg-raised text-ink-3 shadow-stratum">
              {submitting && mode === "zip" ? (
                <Loader2 className="h-5 w-5 animate-spin text-ember" />
              ) : (
                <FileArchive className="h-5 w-5" />
              )}
            </div>
            <p className="mt-4 text-sm font-medium text-ink">Or drop a repository archive</p>
            <p className="mt-1 font-mono text-[11px] tracking-[0.1em] text-ink-3">
              .ZIP · UP TO {MAX_ZIP_MB} MB
            </p>
            {error && mode === "zip" && <p className="mt-3 font-mono text-[13px] text-rust">{error}</p>}
          </div>
        </motion.div>

        {/* What happens next — the pipeline, annotated. */}
        <motion.div variants={fadeInUp}>
          <Card className="p-6">
            <Overline>Pipeline · 6 stages</Overline>
            <ol className="mt-4 grid gap-x-6 gap-y-3 font-mono text-[13px] sm:grid-cols-2">
              {[
                ["01", "Validate", "verify source and access"],
                ["02", "Clone", "fetch the working tree"],
                ["03", "Parse", "tree-sitter symbol extraction"],
                ["04", "Graph", "map calls and imports"],
                ["05", "Index", "persist to the knowledge graph"],
                ["06", "Embed", "vectorize semantic chunks"],
              ].map(([num, label, desc]) => (
                <li key={num} className="flex items-baseline gap-3">
                  <span className="text-ink-3">{num}</span>
                  <span className="text-ink">{label}</span>
                  <span className="hidden truncate text-ink-3 lg:inline">— {desc}</span>
                </li>
              ))}
            </ol>
          </Card>
        </motion.div>

        <motion.div
          variants={fadeInUp}
          className="flex items-center justify-center gap-6 font-mono text-[11px] tracking-[0.1em] text-ink-3"
        >
          <span className="inline-flex items-center gap-1.5">
            <Lock className="h-3 w-3" /> READ-ONLY ACCESS
          </span>
          <span className="inline-flex items-center gap-1.5">
            <CheckCircle2 className="h-3 w-3 text-moss" /> TREE CLEANED AFTER SCAN
          </span>
        </motion.div>
      </motion.div>
    </div>
  );
}
