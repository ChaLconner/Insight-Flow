"use client";

import React, { memo } from "react";
import { Button } from "@/components/ui/button";
import { AlertCircle, RefreshCw, Home } from "lucide-react";
import Link from "next/link";

interface DashboardErrorProps {
  error: Error | string | null;
  onRetry?: () => void;
  isRetrying?: boolean;
}

const DashboardError = memo(function DashboardError({
  error,
  onRetry,
  isRetrying = false,
}: DashboardErrorProps) {
  const errorMessage =
    typeof error === "string"
      ? error
      : (error?.message ?? "An unexpected error occurred");

  return (
    <div
      className="flex flex-col items-center justify-center h-[60vh] space-y-6 px-4"
      role="alert"
      aria-live="assertive"
    >
      {/* Error Icon */}
      <div className="h-16 w-16 rounded-full bg-red-500/10 flex items-center justify-center">
        <AlertCircle className="h-8 w-8 text-red-400" />
      </div>

      {/* Error Message */}
      <div className="text-center space-y-2 max-w-md">
        <h3 className="text-xl font-semibold text-white">
          Failed to load dashboard
        </h3>
        <p className="text-zinc-400">{errorMessage}</p>
      </div>

      {/* Action Buttons */}
      <div className="flex items-center gap-3">
        {onRetry && (
          <Button
            onClick={onRetry}
            disabled={isRetrying}
            className="bg-indigo-600 hover:bg-indigo-500 text-white cursor-pointer"
            aria-label="Retry loading dashboard"
          >
            <RefreshCw
              className={`h-4 w-4 mr-2 ${isRetrying ? "animate-spin" : ""}`}
            />
            {isRetrying ? "Retrying..." : "Try Again"}
          </Button>
        )}

        <Button
          variant="outline"
          className="glass border-white/10 text-zinc-300 hover:text-white hover:bg-white/10 cursor-pointer"
          asChild
        >
          <Link href="/">
            <Home className="h-4 w-4 mr-2" />
            Go Home
          </Link>
        </Button>
      </div>

      {/* Help Text */}
      <p className="text-xs text-zinc-500 text-center">
        If this problem persists, please contact support or try again later.
      </p>
    </div>
  );
});

DashboardError.displayName = "DashboardError";

export { DashboardError };
