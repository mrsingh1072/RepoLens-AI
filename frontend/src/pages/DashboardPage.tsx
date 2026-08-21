import { useMemo, useState } from "react";
import { motion } from "framer-motion";
import {
  Boxes,
  CheckSquare,
  Database,
  FileCode2,
  FolderGit2,
  MessageSquareText,
  Plus,
  Trash2,
  X,
} from "lucide-react";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";

import { EmptyState } from "@/components/common/EmptyState";
import { Overline } from "@/components/common/Overline";
import { PageHeader } from "@/components/common/PageHeader";
import { RepoCard } from "@/components/common/RepoCard";
import { StatCard } from "@/components/common/StatCard";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Skeleton } from "@/components/ui/skeleton";
import { mockActivity } from "@/data/mock";
import { useSimulatedLoading } from "@/hooks/useSimulatedLoading";
import { useRepoStore } from "@/store/repoStore";
import { formatCompact } from "@/utils/format";
import { removeRepositoriesFromBackend } from "@/utils/repositoryCleanup";
import { staggerContainer } from "@/utils/motion";
import { cn } from "@/utils/cn";
import type { ActivityItem } from "@/types";

/* Activity intent — dots, not fills. */
const ACTIVITY_DOT: Record<ActivityItem["type"], string> = {
  index: "bg-moss",
  query: "bg-ember",
  upload: "bg-gold",
  error: "bg-rust",
};

export function DashboardPage() {
  const navigate = useNavigate();
  const repositories = useRepoStore((s) => s.repositories);
  const removeRepositories = useRepoStore((s) => s.removeRepositories);
  const { isLoading } = useSimulatedLoading({ delay: 800 });

  const [selectionMode, setSelectionMode] = useState(false);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [bulkConfirmOpen, setBulkConfirmOpen] = useState(false);
  const [bulkRemoving, setBulkRemoving] = useState(false);

  const selectedRepos = useMemo(
    () => repositories.filter((repo) => selectedIds.has(repo.id)),
    [repositories, selectedIds],
  );

  const totalChunks = repositories.reduce((acc, r) => acc + r.chunks, 0);
  const totalFiles = repositories.reduce((acc, r) => acc + r.files, 0);
  const indexed = repositories.filter((r) => r.status === "indexed").length;
  const anyIndexing = repositories.some((r) => r.status === "indexing");

  const exitSelectionMode = () => {
    setSelectionMode(false);
    setSelectedIds(new Set());
  };

  const toggleSelect = (id: string) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const selectAll = () => setSelectedIds(new Set(repositories.map((r) => r.id)));
  const deselectAll = () => setSelectedIds(new Set());

  const handleBulkRemove = async () => {
    if (!selectedRepos.length) return;
    setBulkRemoving(true);
    try {
      const { removed, failed } = await removeRepositoriesFromBackend(selectedRepos);
      if (removed.length) {
        removeRepositories(removed.map((repo) => repo.id));
      }

      if (removed.length && !failed.length) {
        toast.success(
          removed.length === 1 ? "Repository removed" : `${removed.length} repositories removed`,
          { description: "Selected repositories were deleted from your workspace." },
        );
        exitSelectionMode();
        setBulkConfirmOpen(false);
      } else if (removed.length && failed.length) {
        toast.warning(`Removed ${removed.length}, failed ${failed.length}`, {
          description: failed.map((f) => `${f.repo.owner}/${f.repo.name}`).join(", "),
        });
        setSelectedIds(new Set(failed.map((f) => f.repo.id)));
        setBulkConfirmOpen(false);
      } else if (failed.length) {
        toast.error("Failed to remove repositories", {
          description: failed[0].error,
        });
      }
    } finally {
      setBulkRemoving(false);
    }
  };

  return (
    <div className="space-y-8">
      <PageHeader
        overline="Workspace"
        title="Dashboard"
        description="Your indexed repositories and recent activity, at rest."
        actions={
          <Button
            onClick={() => navigate("/upload")}
            className="flex items-center gap-2 rounded-md bg-orange-500 px-4 py-2 text-white shadow-[inset_0_1px_0_rgba(255,255,255,0.2)] transition-all duration-300 hover:shadow-[0_0_15px_-3px_rgba(249,115,22,0.4)]"
          >
            <Plus />
            Add repository
          </Button>
        }
      />

      <motion.div
        variants={staggerContainer(0.05)}
        initial="hidden"
        animate="show"
        className="grid grid-cols-2 gap-4 lg:grid-cols-4"
      >
        {isLoading ? (
          Array.from({ length: 4 }).map((_, i) => <Skeleton key={i} className="h-[108px] rounded-lg" />)
        ) : (
          <>
            <StatCard label="Repositories" value={`${repositories.length}`} icon={<FolderGit2 />} />
            <StatCard label="Files indexed" value={formatCompact(totalFiles)} icon={<FileCode2 />} />
            <StatCard label="Vector chunks" value={formatCompact(totalChunks)} icon={<Database />} />
            <StatCard
              label="Indexed"
              value={`${indexed}/${repositories.length}`}
              icon={<Boxes />}
              live={anyIndexing}
            />
          </>
        )}
      </motion.div>

      <div className="grid gap-6 lg:grid-cols-3">
        <div className="lg:col-span-2">
          <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
            <Overline>Repositories</Overline>
            <div className="flex flex-wrap items-center gap-2">
              {selectionMode ? (
                <>
                  <span className="tnum font-mono text-[11px] text-ink-3">
                    {selectedIds.size} selected
                  </span>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={selectedIds.size === repositories.length ? deselectAll : selectAll}
                  >
                    <CheckSquare />
                    {selectedIds.size === repositories.length ? "Deselect all" : "Select all"}
                  </Button>
                  <Button
                    variant="destructive"
                    size="sm"
                    disabled={selectedIds.size === 0}
                    onClick={() => setBulkConfirmOpen(true)}
                  >
                    <Trash2 />
                    Remove ({selectedIds.size})
                  </Button>
                  <Button variant="secondary" size="sm" onClick={exitSelectionMode}>
                    <X />
                    Cancel
                  </Button>
                </>
              ) : (
                repositories.length > 0 && (
                  <Button variant="ghost" size="sm" onClick={() => setSelectionMode(true)}>
                    <CheckSquare />
                    Select
                  </Button>
                )
              )}
            </div>
          </div>

          {isLoading ? (
            <div className="grid gap-4 sm:grid-cols-2">
              {Array.from({ length: 4 }).map((_, i) => (
                <Skeleton key={i} className="h-[196px] rounded-lg" />
              ))}
            </div>
          ) : repositories.length === 0 ? (
            <EmptyState
              overline="EMPTY · NO REPOSITORIES"
              icon={<FolderGit2 />}
              title="No repositories yet"
              description="Connect your first GitHub repository to start asking questions about your code."
              action={
                <Button onClick={() => navigate("/upload")}>
                  <Plus />
                  Add repository
                </Button>
              }
            />
          ) : (
            <motion.div
              variants={staggerContainer(0.05)}
              initial="hidden"
              animate="show"
              className="grid gap-4 sm:grid-cols-2"
            >
              {repositories.map((repo) => (
                <RepoCard
                  key={repo.id}
                  repo={repo}
                  selectionMode={selectionMode}
                  selected={selectedIds.has(repo.id)}
                  onToggleSelect={toggleSelect}
                />
              ))}
            </motion.div>
          )}
        </div>

        <div>
          <Overline className="mb-4">Recent activity</Overline>
          <Card>
            <CardContent className="p-2">
              {isLoading ? (
                <div className="space-y-3 p-3">
                  {Array.from({ length: 4 }).map((_, i) => (
                    <div key={i} className="flex items-center gap-3">
                      <Skeleton className="h-2 w-2 rounded-full" />
                      <div className="flex-1 space-y-1.5">
                        <Skeleton className="h-3 w-2/3" />
                        <Skeleton className="h-3 w-1/2" />
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <ul className="divide-y divide-edge">
                  {mockActivity.map((item) => (
                    <li
                      key={item.id}
                      className="flex items-start gap-3 rounded-md p-3 transition-colors hover:bg-raised/60"
                    >
                      <span
                        className={cn("mt-1.5 h-2 w-2 shrink-0 rounded-full", ACTIVITY_DOT[item.type])}
                        aria-hidden
                      />
                      <div className="min-w-0 flex-1">
                        <p className="truncate text-sm font-medium text-ink">{item.title}</p>
                        <p className="mt-0.5 truncate font-mono text-[11px] text-ink-3">{item.detail}</p>
                      </div>
                      <span className="whitespace-nowrap font-mono text-[11px] text-ink-3">
                        {item.time}
                      </span>
                    </li>
                  ))}
                </ul>
              )}
            </CardContent>
          </Card>

          <Card className="mt-4 p-5 transition-all duration-200 hover:border-zinc-700/50 hover:bg-zinc-900/50">
            <Overline>Ask the codebase</Overline>
            <p className="mt-2.5 text-sm leading-relaxed text-ink-2">
              Jump straight into a conversation with your selected repository.
            </p>
            <Button variant="secondary" className="mt-4 w-full" onClick={() => navigate("/chat")}>
              <MessageSquareText />
              Open chat
            </Button>
          </Card>
        </div>
      </div>

      <Dialog open={bulkConfirmOpen} onOpenChange={setBulkConfirmOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>
              Remove {selectedIds.size} {selectedIds.size === 1 ? "repository" : "repositories"}?
            </DialogTitle>
            <DialogDescription>
              This permanently deletes the selected repositories from your workspace, including
              parse data, embeddings, and graph indexes. This cannot be undone.
            </DialogDescription>
          </DialogHeader>
          <ul className="max-h-40 space-y-1 overflow-y-auto rounded-md border border-edge bg-raised p-3 font-mono text-xs text-ink-2">
            {selectedRepos.slice(0, 12).map((repo) => (
              <li key={repo.id} className="truncate">
                {repo.owner}/{repo.name}
              </li>
            ))}
            {selectedRepos.length > 12 && <li className="text-ink-3">+ {selectedRepos.length - 12} more</li>}
          </ul>
          <DialogFooter>
            <DialogClose asChild>
              <Button variant="secondary" disabled={bulkRemoving}>
                Cancel
              </Button>
            </DialogClose>
            <Button variant="destructive" onClick={handleBulkRemove} disabled={bulkRemoving}>
              <Trash2 />
              {bulkRemoving ? "Removing…" : `Remove ${selectedIds.size}`}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
