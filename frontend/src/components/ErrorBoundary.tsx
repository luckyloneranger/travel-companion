import { Component } from 'react';
import type { ErrorInfo, ReactNode } from 'react';

interface Props {
  children: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false, error: null };

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error('ErrorBoundary caught:', error, info.componentStack);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="flex min-h-screen items-center justify-center bg-surface-dim p-8">
          <div className="max-w-md rounded-lg border border-red-200 dark:border-red-800 bg-red-50 dark:bg-red-950/50 p-6 text-center">
            <h2 className="text-lg font-semibold text-red-800 dark:text-red-300">Something went wrong</h2>
            <p className="mt-2 text-sm text-red-600 dark:text-red-400">
              {this.state.error?.message || 'An unexpected error occurred.'}
            </p>
            <button
              type="button"
              onClick={() => window.location.reload()}
              className="mt-4 rounded-md bg-red-600 px-4 py-2 text-sm font-medium text-white hover:bg-red-700"
            >
              Reload Page
            </button>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
