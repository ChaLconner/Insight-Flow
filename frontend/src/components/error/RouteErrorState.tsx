"use client";

import { useEffect } from "react";
import Link from "next/link";
import { AlertCircle, Home, RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";

interface RouteErrorStateProps {
  error: Error & { digest?: string };
  reset: () => void;
  title: string;
  fallbackMessage: string;
}

export function RouteErrorState({
  error,
  reset,
  title,
  fallbackMessage,
}: Readonly<RouteErrorStateProps>) {
  useEffect(() => {
    console.error(error);
  }, [error]);

  return (
    <div className="flex flex-col items-center justify-center min-h-[60vh] space-y-6 px-4 pt-24">
      <div className="h-16 w-16 rounded-full bg-red-500/10 flex items-center justify-center">
        <AlertCircle className="h-8 w-8 text-red-400" />
      </div>

      <div className="text-center space-y-2 max-w-md">
        <h3 className="text-xl font-semibold text-white">{title}</h3>
        <p className="text-zinc-400">{error.message || fallbackMessage}</p>
      </div>

      <div className="flex items-center gap-3">
        <Button
          onClick={reset}
          className="bg-indigo-600 hover:bg-indigo-500 text-white cursor-pointer"
        >
          <RefreshCw className="h-4 w-4 mr-2" />
          Try Again
        </Button>

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
    </div>
  );
}
