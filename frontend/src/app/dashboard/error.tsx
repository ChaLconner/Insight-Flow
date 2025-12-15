"use client";

import { useEffect } from "react";
import { DashboardError } from "./components/DashboardError";

export default function ErrorPage({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    // Log the error to an error reporting service
    console.error(error);
  }, [error]);

  return (
    <div className="pt-24 min-h-screen bg-black">
      <DashboardError error={error} onRetry={reset} />
    </div>
  );
}
