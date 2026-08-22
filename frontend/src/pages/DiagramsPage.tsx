import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Layers, Loader2, Network, Workflow } from "lucide-react";
import { useLocation } from "react-router-dom";

import { fetchDiagrams, type DiagramBundle } from "@/api/diagrams";
import { toApiErrorMessage } from "@/api/client";
import { ErrorState } from "@/components/common/ErrorState";
import { PageHeader } from "@/components/common/PageHeader";
import { ExportToolbar } from "@/components/diagrams/ExportToolbar";
import { graphViewToFlow, cleanupMermaidArtifacts } from "@/components/diagrams/diagramUtils";
import { InteractiveGraph } from "@/components/diagrams/InteractiveGraph";
import { MermaidPanel } from "@/components/diagrams/MermaidPanel";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useRepoStore } from "@/store/repoStore";
import { encodeRepoId, repoIdFromSelection } from "@/utils/repoId";

export type DiagramTab = "system" | "dependency" | "mermaid";
export type DiagramView = DiagramTab | "all";

interface DiagramsPageProps {
  /** When set, show only this view (no tab switcher). */
  view?: DiagramView;
}

const VIEW_META: Record<
  Exclude<DiagramView, "all">,
  { overline: string; title: string; description: string; icon: typeof Workflow }
> = {
  system: {
    overline: "Map room · System",
    title: "Architecture Explorer",
    description: "Layered view of the system: frontend → API → services → data.",
    icon: Workflow,
  },
  dependency: {
    overline: "Map room · Imports",
    title: "Dependency Graph",
    description: "Module import relationships across the codebase.",
    icon: Network,
  },
  mermaid: {
    overline: "Map room · Diagrams",
    title: "Mermaid Diagrams",
    description: "Flowchart, sequence, and class diagrams.",
    icon: Layers,
  },
};

function tabFromPath(pathname: string): DiagramTab {
  if (pathname.startsWith("/dependencies")) return "dependency";
  if (pathname.startsWith("/architecture")) return "system";
  return "system";
}

export function DiagramsPage({ view = "all" }: DiagramsPageProps) {
  const location = useLocation();
  const repositories = useRepoStore((s) => s.repositories);
  const selectedId = useRepoStore((s) => s.selectedRepoId);
  const activeRepo = repositories.find((r) => r.id === selectedId) ?? repositories[0];

  const routeTab = tabFromPath(location.pathname);
  const [tab, setTab] = useState<DiagramTab>(view === "all" ? routeTab : view);
  const [bundle, setBundle] = useState<DiagramBundle | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const viewportRef = useRef<HTMLDivElement>(null);

  const activeView: DiagramTab = view === "all" ? tab : view;

  useEffect(() => {
    if (view === "all") {
      setTab(routeTab);
    }
  }, [view, routeTab]);

  useEffect(() => {
    cleanupMermaidArtifacts();
  }, [activeView]);

  const load = useCallback(async () => {
    if (!activeRepo) {
      setError("Select or ingest a repository first.");
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const repoId = repoIdFromSelection(activeRepo.owner, activeRepo.name);
      const data = await fetchDiagrams(encodeRepoId(repoId));
      setBundle(data);
    } catch (err) {
      setError(toApiErrorMessage(err));
      setBundle(null);
    } finally {
      setLoading(false);
    }
  }, [activeRepo]);

  useEffect(() => {
    void load();
  }, [load]);

  const systemFlow = useMemo(
    () =>
      bundle
        ? graphViewToFlow(bundle.system_architecture, "system")
        : { nodes: [], edges: [], truncated: false },
    [bundle],
  );
  const depFlow = useMemo(
    () =>
      bundle
        ? graphViewToFlow(bundle.dependency_graph, "dependency")
        : { nodes: [], edges: [], truncated: false },
    [bundle],
  );

  const meta = VIEW_META[activeView === "mermaid" ? "mermaid" : activeView];

  const renderSystem = () => (
    <>
      <InteractiveGraph
        graphKey={`system-${bundle?.repo_id ?? "none"}`}
        nodes={systemFlow.nodes}
        edges={systemFlow.edges}
        exportRef={viewportRef}
        emptyMessage="No system architecture graph indexed for this repository."
      />
      <p className="tnum mt-2.5 text-center font-mono text-[11px] text-ink-3">
        PAN · ZOOM · DRAG — {systemFlow.nodes.length} components, {systemFlow.edges.length} links
      </p>
    </>
  );

  const renderDependency = () => (
    <>
      <InteractiveGraph
        graphKey={`dependency-${bundle?.repo_id ?? "none"}`}
        nodes={depFlow.nodes}
        edges={depFlow.edges}
        exportRef={viewportRef}
        emptyMessage="No import/dependency edges indexed for this repository."
      />
      <p className="tnum mt-2.5 text-center font-mono text-[11px] text-ink-3">
        {depFlow.truncated ? `TOP ${depFlow.nodes.length} MODULES BY CONNECTIVITY — ` : ""}
        {depFlow.nodes.length} modules, {depFlow.edges.length} imports
      </p>
    </>
  );

  const renderMermaid = () => (
    <div ref={viewportRef} className="grid gap-6 lg:grid-cols-2">
      <MermaidPanel title="Flowchart" source={bundle!.mermaid.flowchart} />
      <MermaidPanel title="Sequence diagram" source={bundle!.mermaid.sequence} />
      <div className="lg:col-span-2">
        <MermaidPanel title="Class diagram" source={bundle!.mermaid.class_diagram} />
      </div>
    </div>
  );

  return (
    <div className="space-y-6">
      <PageHeader
        overline={
          activeRepo ? `${meta.overline} · ${activeRepo.owner}/${activeRepo.name}` : meta.overline
        }
        title={view === "all" ? "Architecture Diagrams" : meta.title}
        description={meta.description}
        actions={
          bundle ? (
            <ExportToolbar bundle={bundle} viewportRef={viewportRef} activeTab={activeView} />
          ) : loading ? (
            <Loader2 className="h-4 w-4 animate-spin text-ink-3" />
          ) : null
        }
      />

      {loading ? (
        <Skeleton className="h-[620px] w-full rounded-lg" />
      ) : error ? (
        <ErrorState description={error} onRetry={load} />
      ) : bundle && view !== "all" ? (
        activeView === "system" ? (
          renderSystem()
        ) : activeView === "dependency" ? (
          renderDependency()
        ) : (
          renderMermaid()
        )
      ) : bundle ? (
        <Tabs value={tab} onValueChange={(v) => setTab(v as DiagramTab)}>
          <TabsList>
            <TabsTrigger value="system" className="gap-1.5">
              <Layers className="h-3.5 w-3.5" />
              System
            </TabsTrigger>
            <TabsTrigger value="dependency" className="gap-1.5">
              <Network className="h-3.5 w-3.5" />
              Dependencies
            </TabsTrigger>
            <TabsTrigger value="mermaid" className="gap-1.5">
              <Workflow className="h-3.5 w-3.5" />
              Mermaid
            </TabsTrigger>
          </TabsList>

          <TabsContent value="system" className="mt-5">
            {tab === "system" && renderSystem()}
          </TabsContent>
          <TabsContent value="dependency" className="mt-5">
            {tab === "dependency" && renderDependency()}
          </TabsContent>
          <TabsContent value="mermaid" className="mt-5">
            {tab === "mermaid" && renderMermaid()}
          </TabsContent>
        </Tabs>
      ) : null}
    </div>
  );
}
