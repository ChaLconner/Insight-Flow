"use client";

import { RouteErrorState } from "@/components/error/RouteErrorState";

export default function ProjectsError({
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
      title="Failed to load projects"
      fallbackMessage="An unexpected error occurred while loading your projects."
    />
  );
}
