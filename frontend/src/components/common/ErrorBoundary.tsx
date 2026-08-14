import { Component, type ErrorInfo, type ReactNode } from "react";
import { AlertTriangle, RefreshCw } from "lucide-react";

import { Button } from "@/components/ui/button";

interface Props {
  children: ReactNode;
  fallbackTitle?: string;
}

interface State {
  hasError: boolean;
  message: string;
}

/** Catches render errors and shows a recoverable fallback UI. */
export class ErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false, message: "" };

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, message: error.message || "Something went wrong." };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error("UI error boundary caught:", error, info);
  }

  private reset = () => {
    this.setState({ hasError: false, message: "" });
  };

  render() {
    if (!this.state.hasError) {
      return this.props.children;
    }

    return (
      <div
        role="alert"
        aria-live="assertive"
        className="flex min-h-[320px] flex-col items-center justify-center rounded-lg border border-dashed border-edge px-6 py-12 text-center"
      >
        <span className="overline-label mb-5 text-rust">ERR · RUNTIME</span>
        <div className="mb-4 flex h-14 w-14 items-center justify-center rounded-lg border border-rust/30 bg-raised text-rust shadow-stratum">
          <AlertTriangle className="h-6 w-6" aria-hidden />
        </div>
        <h2 className="font-display text-lg font-semibold text-ink">
          {this.props.fallbackTitle ?? "Something went wrong"}
        </h2>
        <p className="mt-2 max-w-md text-sm leading-relaxed text-ink-2">{this.state.message}</p>
        <div className="mt-6 flex gap-2">
          <Button variant="secondary" onClick={this.reset}>
            Try again
          </Button>
          <Button variant="ghost" onClick={() => window.location.reload()}>
            <RefreshCw />
            Reload page
          </Button>
        </div>
      </div>
    );
  }
}
