import { Suspense, type ReactNode } from "react";

import { ErrorBoundary } from "@/components/common/ErrorBoundary";
import { PageSkeleton } from "@/components/common/PageSkeleton";

/** Wraps lazy routes with error recovery and a skeleton fallback. */
export function LazyPage({ children }: { children: ReactNode }) {
  return (
    <ErrorBoundary>
      <Suspense fallback={<PageSkeleton />}>{children}</Suspense>
    </ErrorBoundary>
  );
}
