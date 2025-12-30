"use client";

import type { ErrorInfo, ReactNode } from "react";
import React, { Component } from "react";
import { Button } from "@/components/ui/button";
import { AlertCircle } from "lucide-react";
import { cn } from "@/lib/utils";

interface Props {
  children?: ReactNode;
  fallback?: ReactNode;
  className?: string;
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
    if (!this.props.fallback) {
      window.location.reload();
    }
  };

  public render() {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback;
      }

      return (
        <div 
          className={cn(
            "flex flex-col items-center justify-center p-4 text-foreground",
            !this.props.className && "min-h-[400px] w-full",
            this.props.className
          )}
        >
          <div className="p-8 max-w-md w-full rounded-2xl border border-border/50 bg-card/30 backdrop-blur-xl shadow-2xl text-center space-y-6">
            <div className="mx-auto w-16 h-16 rounded-full bg-red-500/10 flex items-center justify-center">
              <AlertCircle className="w-8 h-8 text-red-500" />
            </div>
            <div className="space-y-2">
              <h2 className="text-2xl font-bold bg-gradient-to-r from-red-500 to-pink-500 bg-clip-text text-transparent">
                Something went wrong
              </h2>
              <p className="text-muted-foreground text-sm">
                We encountered an unexpected error while rendering this component.
              </p>
            </div>
            
            {this.state.error && (
              <div className="p-3 rounded-lg bg-red-500/5 border border-red-500/10 text-left overflow-auto max-h-32 text-[10px] font-mono text-red-400/80">
                {this.state.error.message}
              </div>
            )}
            
            <Button
              onClick={this.handleRetry}
              variant="outline"
              className="w-full border-red-500/20 hover:bg-red-500/10 text-red-500"
            >
              Try again
            </Button>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
