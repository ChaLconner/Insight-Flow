"use client";

import type { ErrorInfo, ReactNode } from "react";
import React, { Component } from "react";
import { Button } from "@/components/ui/button";

interface Props {
  children?: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
  public state: State = {
    hasError: false,
    error: null,
  };

  public static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error("Uncaught error:", error, errorInfo);
  }

  private readonly handleRetry = () => {
    this.setState({ hasError: false, error: null });
    window.location.reload();
  };

  public render() {
    if (this.state.hasError) {
      return (
        <div className="flex flex-col items-center justify-center min-h-screen p-4 bg-background text-foreground">
          <div className="p-8 max-w-md w-full rounded-2xl border border-border/50 bg-card/30 backdrop-blur-xl shadow-2xl text-center space-y-6">
            <h2 className="text-3xl font-bold bg-gradient-to-r from-red-500 to-pink-500 bg-clip-text text-transparent">
              Something went wrong
            </h2>
            <p className="text-muted-foreground">
              We encountered an unexpected error. Please try again.
            </p>
            {this.state.error && (
              <div className="p-4 rounded-lg bg-red-500/10 border border-red-500/20 text-left overflow-auto max-h-40 text-xs font-mono text-red-400">
                {this.state.error.message}
              </div>
            )}
            <Button
              onClick={this.handleRetry}
              variant="default"
              className="w-full shadow-lg shadow-primary/25"
            >
              Reload Application
            </Button>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
