import React from 'react';

interface ErrorBoundaryProps {
  children: React.ReactNode;
  fallback?: React.ReactNode;
}

interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends React.Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo): void {
    console.error('[ErrorBoundary] Caught error:', error, errorInfo);
  }

  handleRetry = () => {
    this.setState({ hasError: false, error: null });
  };

  handleReload = () => {
    window.location.reload();
  };

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback;
      }

      return (
        <div
          role="alert"
          aria-label="Application error"
          className="flex flex-col items-center justify-center h-full w-full bg-[#09090b] text-white p-8"
        >
          <div className="max-w-md text-center space-y-6">
            <div className="w-16 h-16 mx-auto rounded-full bg-red-500/10 border border-red-500/20 flex items-center justify-center" aria-hidden="true">
              <svg className="w-8 h-8 text-red-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L4.082 16.5c-.77.833.192 2.5 1.732 2.5z" />
              </svg>
            </div>
            <h2 className="text-xl font-black uppercase tracking-tighter">System Error</h2>
            <p className="text-sm text-zinc-400 font-mono">
              {process.env.NODE_ENV === 'development'
                ? (this.state.error?.message || 'An unexpected error occurred.')
                : 'An unexpected error occurred. Please try again.'}
            </p>
            <div className="flex gap-3 justify-center">
              <button
                onClick={this.handleRetry}
                aria-label="Retry loading the application"
                className="px-4 py-2 bg-emerald-500/10 border border-emerald-500/20 text-emerald-500 rounded-lg text-xs font-bold uppercase tracking-widest hover:bg-emerald-500/20 transition-colors"
              >
                Retry
              </button>
              <button
                onClick={this.handleReload}
                aria-label="Reload the page"
                className="px-4 py-2 bg-zinc-800 border border-white/10 text-zinc-400 rounded-lg text-xs font-bold uppercase tracking-widest hover:bg-zinc-700 transition-colors"
              >
                Reload Page
              </button>
            </div>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

export default ErrorBoundary;
