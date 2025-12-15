import React, { memo } from "react";
import { Button } from "@/components/ui/button";
import { ProtectedLayout } from "@/components/layout/ProtectedLayout";
import { RefreshCw, AlertCircle } from "lucide-react";

interface AnalyticsErrorProps {
  error: Error | unknown;
  onRetry: () => void;
}

export const AnalyticsError = memo(function AnalyticsError({
  error,
  onRetry,
}: AnalyticsErrorProps) {
  return (
    <ProtectedLayout>
      <div className="flex flex-col items-center justify-center h-64 space-y-4">
        <div className="flex flex-col items-center text-center">
          <div className="w-16 h-16 rounded-full bg-red-500/10 flex items-center justify-center mb-4">
            <AlertCircle className="w-8 h-8 text-red-400" />
          </div>
          <h3 className="text-lg font-semibold text-white mb-2">
            Failed to Load Analytics
          </h3>
          <p className="text-zinc-400 max-w-md mb-4">
            {error instanceof Error
              ? error.message
              : "An unexpected error occurred while loading analytics data."}
          </p>
          <Button
            onClick={onRetry}
            className="bg-gradient-to-r from-indigo-600 to-violet-600 hover:from-indigo-500 hover:to-violet-500 text-white gap-2 cursor-pointer"
          >
            <RefreshCw className="w-4 h-4" />
            Try Again
          </Button>
        </div>
      </div>
    </ProtectedLayout>
  );
});
