import { lazy, Suspense } from "react";
import { BrowserRouter, Route, Routes } from "react-router-dom";

import { ErrorBoundary } from "@/components/common/ErrorBoundary";
import { LazyPage } from "@/components/common/LazyPage";
import { PageSkeleton } from "@/components/common/PageSkeleton";
import { AppLayout } from "@/components/layout/AppLayout";
import { TooltipProvider } from "@/components/ui/tooltip";
import { LandingPage } from "@/pages/LandingPage";
import { NotFoundPage } from "@/pages/NotFoundPage";

const DashboardPage = lazy(() =>
  import("@/pages/DashboardPage").then((m) => ({ default: m.DashboardPage })),
);
const UploadRepositoryPage = lazy(() =>
  import("@/pages/UploadRepositoryPage").then((m) => ({ default: m.UploadRepositoryPage })),
);
const RepositoryOverviewPage = lazy(() =>
  import("@/pages/RepositoryOverviewPage").then((m) => ({ default: m.RepositoryOverviewPage })),
);
const ChatPage = lazy(() => import("@/pages/ChatPage").then((m) => ({ default: m.ChatPage })));
const AnalyticsPage = lazy(() =>
  import("@/pages/AnalyticsPage").then((m) => ({ default: m.AnalyticsPage })),
);
const ArchitecturePage = lazy(() =>
  import("@/pages/ArchitecturePage").then((m) => ({ default: m.ArchitecturePage })),
);
const DependencyGraphPage = lazy(() =>
  import("@/pages/DependencyGraphPage").then((m) => ({ default: m.DependencyGraphPage })),
);
const DiagramsPage = lazy(() =>
  import("@/pages/DiagramsPage").then((m) => ({ default: m.DiagramsPage })),
);
const SettingsPage = lazy(() =>
  import("@/pages/SettingsPage").then((m) => ({ default: m.SettingsPage })),
);

/** Root application component and route table. */
export default function App() {
  return (
    <TooltipProvider delayDuration={200}>
      <ErrorBoundary fallbackTitle="Application error">
        <BrowserRouter>
          <Routes>
            <Route path="/" element={<LandingPage />} />

            <Route element={<AppLayout />}>
              <Route
                path="/dashboard"
                element={
                  <LazyPage>
                    <DashboardPage />
                  </LazyPage>
                }
              />
              <Route
                path="/upload"
                element={
                  <LazyPage>
                    <UploadRepositoryPage />
                  </LazyPage>
                }
              />
              <Route
                path="/repository"
                element={
                  <LazyPage>
                    <RepositoryOverviewPage />
                  </LazyPage>
                }
              />
              <Route
                path="/repository/:id"
                element={
                  <LazyPage>
                    <RepositoryOverviewPage />
                  </LazyPage>
                }
              />
              <Route
                path="/chat"
                element={
                  <LazyPage>
                    <ChatPage />
                  </LazyPage>
                }
              />
              <Route
                path="/analytics"
                element={
                  <LazyPage>
                    <AnalyticsPage />
                  </LazyPage>
                }
              />
              <Route
                path="/architecture"
                element={
                  <LazyPage>
                    <ArchitecturePage />
                  </LazyPage>
                }
              />
              <Route
                path="/dependencies"
                element={
                  <LazyPage>
                    <DependencyGraphPage />
                  </LazyPage>
                }
              />
              <Route
                path="/diagrams"
                element={
                  <LazyPage>
                    <DiagramsPage />
                  </LazyPage>
                }
              />
              <Route
                path="/settings"
                element={
                  <LazyPage>
                    <SettingsPage />
                  </LazyPage>
                }
              />
            </Route>

            <Route
              path="*"
              element={
                <Suspense fallback={<PageSkeleton />}>
                  <NotFoundPage />
                </Suspense>
              }
            />
          </Routes>
        </BrowserRouter>
      </ErrorBoundary>
    </TooltipProvider>
  );
}
