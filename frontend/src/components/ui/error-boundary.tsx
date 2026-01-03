"use client";

import { Component, ReactNode } from "react";
import { AlertTriangle, RefreshCw } from "lucide-react";
import { Button } from "./button";
import { Card, CardContent } from "./card";

interface ErrorBoundaryProps {
  children: ReactNode;
  fallback?: ReactNode;
  onReset?: () => void;
}

interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends Component<
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
    console.error("ErrorBoundary caught an error:", error, errorInfo);
  }

  handleReset = () => {
    this.setState({ hasError: false, error: null });
    this.props.onReset?.();
  };

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback;
      }

      return (
        <ErrorFallback
          error={this.state.error}
          onReset={this.handleReset}
        />
      );
    }

    return this.props.children;
  }
}

interface ErrorFallbackProps {
  error: Error | null;
  onReset?: () => void;
  title?: string;
  description?: string;
}

export function ErrorFallback({
  error,
  onReset,
  title = "Something went wrong",
  description,
}: ErrorFallbackProps) {
  const errorMessage = error?.message || "An unexpected error occurred";
  const errorDescription =
    description ||
    "The application encountered an error. This could be due to a network issue, invalid data, or a bug in the application.";

  return (
    <div className="flex items-center justify-center min-h-[400px] p-md">
      <Card className="max-w-md w-full">
        <CardContent className="text-center py-lg">
          <div className="flex justify-center mb-md">
            <div className="p-md bg-danger-100 rounded-full">
              <AlertTriangle className="h-8 w-8 text-danger-600" />
            </div>
          </div>

          <h2 className="text-xl font-semibold text-gray-900 mb-sm">
            {title}
          </h2>

          <p className="text-gray-600 mb-md">{errorDescription}</p>

          <div className="bg-gray-50 rounded-md p-sm mb-md">
            <p className="text-sm font-medium text-gray-700 mb-xs">
              Error details:
            </p>
            <p className="text-sm text-danger-600 font-mono break-all">
              {errorMessage}
            </p>
          </div>

          <div className="space-y-sm">
            <p className="text-sm text-gray-500">
              Try refreshing the page or going back to the dashboard.
            </p>

            <div className="flex gap-sm justify-center">
              {onReset && (
                <Button variant="secondary" onClick={onReset}>
                  <RefreshCw className="h-4 w-4 mr-2" />
                  Try Again
                </Button>
              )}
              <Button onClick={() => (window.location.href = "/")}>
                Go to Dashboard
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

export function PageErrorFallback({
  error,
  onReset,
}: {
  error: Error | null;
  onReset?: () => void;
}) {
  return (
    <div className="max-w-7xl mx-auto px-md py-lg">
      <ErrorFallback
        error={error}
        onReset={onReset}
        title="Page Error"
        description="This page encountered an error while loading. The error has been logged and we'll look into it."
      />
    </div>
  );
}
