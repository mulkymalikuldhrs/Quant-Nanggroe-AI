"use client";

import React from "react";
import { Button } from "@/components/ui/button";
import { AlertTriangle, RefreshCw } from "lucide-react";

interface ErrorBoundaryProps {
  children: React.ReactNode;
  fallback?: React.ReactNode;
  onError?: (error: Error, errorInfo: React.ErrorInfo) => void;
}

interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends React.Component<
  ErrorBoundaryProps,
  ErrorBoundaryState
> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    console.error("[ErrorBoundary]", error, errorInfo);
    this.props.onError?.(error, errorInfo);
  }

  handleRetry = () => {
    this.setState({ hasError: false, error: null });
  };

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback;
      }

      return (
        <div className="flex flex-col items-center justify-center p-8 rounded-lg border border-red-500/20 bg-red-500/5 text-center space-y-3">
          <div className="p-3 rounded-full bg-red-500/10">
            <AlertTriangle className="w-6 h-6 text-red-400" />
          </div>
          <div>
            <h3 className="text-sm font-semibold text-white/80">
              Something went wrong
            </h3>
            <p className="text-xs text-white/40 mt-1 max-w-md">
              {this.state.error?.message || "An unexpected error occurred"}
            </p>
          </div>
          <Button
            variant="secondary"
            size="sm"
            onClick={this.handleRetry}
            className="text-xs gap-1.5"
          >
            <RefreshCw className="w-3 h-3" />
            Try again
          </Button>
        </div>
      );
    }

    return this.props.children;
  }
}

// ── Inline error display for API errors ───────────────────────────

interface ErrorDisplayProps {
  error: string | null;
  onRetry?: () => void;
  title?: string;
  className?: string;
}

export function ErrorDisplay({
  error,
  onRetry,
  title = "Failed to load data",
  className = "",
}: ErrorDisplayProps) {
  if (!error) return null;

  return (
    <div
      className={`flex items-center gap-3 p-3 rounded-lg border border-red-500/20 bg-red-500/5 ${className}`}
    >
      <AlertTriangle className="w-4 h-4 text-red-400 flex-shrink-0" />
      <div className="flex-1 min-w-0">
        <p className="text-xs font-medium text-red-300">{title}</p>
        <p className="text-[11px] text-white/40 truncate">{error}</p>
      </div>
      {onRetry && (
        <Button
          variant="ghost"
          size="icon"
          onClick={onRetry}
          className="h-7 w-7 flex-shrink-0"
          title="Retry"
        >
          <RefreshCw className="w-3 h-3" />
        </Button>
      )}
    </div>
  );
}
