import { useState } from "react";
import { motion } from "framer-motion";
import { Check, GitFork, MoreHorizontal, Star, Trash2 } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";

import { toApiErrorMessage } from "@/api/client";
import { SpotlightCard } from "@/components/ui/card";
import { RepoStatusBadge } from "@/components/common/RepoStatusBadge";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { useRepoStore } from "@/store/repoStore";
import type { Repository } from "@/types";
import { formatCompact } from "@/utils/format";
import { fadeInUp, settle } from "@/utils/motion";
import { removeRepositoriesFromBackend } from "@/utils/repositoryCleanup";
import { cn } from "@/utils/cn";

/* Language dots — earthy, luminance-separated (see chartTheme). */
const LANGUAGE_COLOR: Record<string, string> = {
  TypeScript: "bg-[hsl(215_14%_58%)]",
  JavaScript: "bg-gold",
  Python: "bg-moss",
  Rust: "bg-ember",
  Go: "bg-[hsl(150_26%_50%)]",
  Java: "bg-[hsl(10_42%_52%)]",
};

interface RepoCardProps {
  repo: Repository;
  selectionMode?: boolean;
  selected?: boolean;
  onToggleSelect?: (id: string) => void;
}

export function RepoCard({
  repo,
  selectionMode = false,
  selected = false,
  onToggleSelect,
}: RepoCardProps) {
  const navigate = useNavigate();
  const selectRepo = useRepoStore((s) => s.selectRepo);
  const removeRepository = useRepoStore((s) => s.removeRepository);
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [removing, setRemoving] = useState(false);

  const open = () => {
    selectRepo(repo.id);
    navigate(`/repository/${repo.id}`);
  };

  const handleCardClick = () => {
    if (selectionMode) {
      onToggleSelect?.(repo.id);
      return;
    }
    open();
  };

  const handleRemove = async () => {
    setRemoving(true);
    try {
      const { removed, failed } = await removeRepositoriesFromBackend([repo]);
      if (removed.length) {
        removeRepository(repo.id);
        setConfirmOpen(false);
        toast.success("Repository removed", {
          description: `${repo.owner}/${repo.name} was deleted from your workspace.`,
        });
      }
      if (failed.length) {
        toast.error("Failed to remove repository", { description: failed[0].error });
      }
    } catch (error) {
      toast.error("Failed to remove repository", {
        description: toApiErrorMessage(error),
      });
    } finally {
      setRemoving(false);
    }
  };

  const isLive = repo.status === "indexing";

  return (
    <>
      <motion.div variants={fadeInUp} className="h-full">
        <SpotlightCard
          onClick={handleCardClick}
          role="button"
          tabIndex={0}
          onKeyDown={(e) => e.key === "Enter" && handleCardClick()}
          className={cn(
            "flex h-full cursor-pointer flex-col p-5",
            selectionMode && selected && "border-ember/50 ring-1 ring-ember/40",
            isLive && "border-ember/25",
          )}
        >
          {selectionMode && (
            <button
              type="button"
              aria-label={selected ? "Deselect repository" : "Select repository"}
              className={cn(
                "absolute left-3.5 top-3.5 z-10 flex h-5 w-5 items-center justify-center rounded-sm border transition-colors",
                selected
                  ? "border-ember bg-ember text-on-ember"
                  : "border-edge-strong bg-raised text-transparent hover:border-ink-3",
              )}
              onClick={(e) => {
                e.stopPropagation();
                onToggleSelect?.(repo.id);
              }}
            >
              <Check className="h-3.5 w-3.5" strokeWidth={3} />
            </button>
          )}

          <div className={cn("flex items-start justify-between gap-3", selectionMode && "pl-7")}>
            <div className="min-w-0">
              <p className="truncate font-mono text-[11px] text-ink-3">{repo.owner}/</p>
              <h3 className="mt-0.5 truncate font-display text-[17px] font-semibold text-ink">
                {repo.name}
              </h3>
            </div>
            <div className="flex items-center gap-1">
              <RepoStatusBadge status={repo.status} />
              {!selectionMode && (
                <DropdownMenu>
                  <DropdownMenuTrigger asChild>
                    <Button
                      type="button"
                      variant="ghost"
                      size="icon-sm"
                      className="shrink-0 opacity-50 transition-opacity hover:opacity-100 group-hover:opacity-100 data-[state=open]:opacity-100"
                      onClick={(e) => e.stopPropagation()}
                      onKeyDown={(e) => e.stopPropagation()}
                      aria-label={`Actions for ${repo.name}`}
                    >
                      <MoreHorizontal className="h-4 w-4" />
                    </Button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent align="end" onClick={(e) => e.stopPropagation()}>
                    <DropdownMenuItem
                      onSelect={(e) => {
                        e.preventDefault();
                        open();
                      }}
                    >
                      Open repository
                    </DropdownMenuItem>
                    <DropdownMenuSeparator />
                    <DropdownMenuItem
                      className="text-rust focus:text-rust"
                      onSelect={(e) => {
                        e.preventDefault();
                        setConfirmOpen(true);
                      }}
                    >
                      <Trash2 />
                      Remove
                    </DropdownMenuItem>
                  </DropdownMenuContent>
                </DropdownMenu>
              )}
            </div>
          </div>

          <p className="mt-2.5 line-clamp-2 flex-1 text-sm leading-relaxed text-ink-2">
            {repo.description}
          </p>

          {isLive && (
            <div className="mt-4">
              <div className="mb-1.5 flex justify-between font-mono text-[11px]">
                <span className="animate-breathe text-ember">INDEXING</span>
                <span className="tnum text-ink-2">{repo.progress}%</span>
              </div>
              <div className="h-1 overflow-hidden rounded-full bg-raised">
                <motion.div
                  className="h-full rounded-full bg-ember"
                  initial={{ width: 0 }}
                  animate={{ width: `${repo.progress}%` }}
                  transition={settle}
                />
              </div>
            </div>
          )}

          <div className="mt-4 flex items-center gap-4 border-t border-edge pt-3.5 font-mono text-[11px] text-ink-3">
            <span className="inline-flex items-center gap-1.5">
              <span className={cn("h-2 w-2 rounded-full", LANGUAGE_COLOR[repo.language] ?? "bg-ink-3/60")} />
              {repo.language}
            </span>
            <span className="tnum inline-flex items-center gap-1">
              <Star className="h-3 w-3" />
              {formatCompact(repo.stars)}
            </span>
            <span className="tnum inline-flex items-center gap-1">
              <GitFork className="h-3 w-3" />
              {formatCompact(repo.forks)}
            </span>
            <span className="ml-auto">{repo.updatedAt}</span>
          </div>
        </SpotlightCard>
      </motion.div>

      <Dialog open={confirmOpen} onOpenChange={setConfirmOpen}>
        <DialogContent showClose={false} onClick={(e) => e.stopPropagation()}>
          <DialogHeader>
            <DialogTitle>Remove repository?</DialogTitle>
            <DialogDescription>
              This permanently deletes{" "}
              <strong className="text-ink">
                {repo.owner}/{repo.name}
              </strong>{" "}
              from your workspace, including parse data, embeddings, and graph indexes. This cannot
              be undone.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <DialogClose asChild>
              <Button variant="secondary" disabled={removing}>
                Cancel
              </Button>
            </DialogClose>
            <Button variant="destructive" onClick={handleRemove} disabled={removing}>
              <Trash2 />
              {removing ? "Removing…" : "Remove"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
