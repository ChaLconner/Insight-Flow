"use client";

import { RouteErrorState } from "@/components/error/RouteErrorState";

export default function AnalyticsError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <RouteErrorState
      error={error}
      reset={reset}
      title="Failed to load analytics"
      fallbackMessage="An unexpected error occurred while loading analytics data."
    />
  );
}
