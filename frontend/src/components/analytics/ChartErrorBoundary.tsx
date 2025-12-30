"use client";

import type { ErrorInfo, ReactNode } from "react";
import React, { Component } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { AlertTriangle, RefreshCw } from "lucide-react";

interface Props {
  children: ReactNode;
  fallbackTitle?: string;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

/**
 * Error Boundary component for gracefully handling chart rendering errors.
 * Provides a fallback UI when a chart component crashes.
 */
export class ChartErrorBoundary extends Component<Props, State> {
  public state: State = {
    hasError: false,
    error: null,
  };

  public static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error("Chart Error:", error);
    console.error("Component Stack:", errorInfo.componentStack);
  }

  private readonly handleRetry = () => {
    this.setState({ hasError: false, error: null });
  };

  public render() {
    if (this.state.hasError) {
      return (
        <Card className="border-border bg-card backdrop-blur-sm h-full flex flex-col">
          <CardHeader>
            <CardTitle className="text-lg font-semibold text-foreground flex items-center gap-2">
              <AlertTriangle className="h-5 w-5 text-amber-400" />
              {this.props.fallbackTitle ?? "Chart Error"}
            </CardTitle>
          </CardHeader>
          <CardContent className="flex-1 flex flex-col items-center justify-center gap-4">
            <p className="text-muted-foreground text-center max-w-sm">
              Something went wrong while rendering this chart. Please try
              refreshing or contact support if the issue persists.
            </p>
            <Button
              variant="outline"
              onClick={this.handleRetry}
              className="flex items-center gap-2 border-border hover:bg-accent"
            >
              <RefreshCw className="h-4 w-4" />
              Try Again
            </Button>
            {process.env.NODE_ENV === "development" && this.state.error && (
              <pre className="text-xs text-red-400 mt-4 p-2 bg-destructive/10 rounded max-w-full overflow-auto">
                {this.state.error.message}
              </pre>
            )}
          </CardContent>
        </Card>
      );
    }

    return this.props.children;
  }
}
