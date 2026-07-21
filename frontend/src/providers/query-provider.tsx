"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { lazy, Suspense } from "react";
import { shouldEnableDevelopmentDiagnostics } from "@/lib/runtime-flags";

const ReactQueryDevtools = lazy(async () => {
  const mod = await import("@tanstack/react-query-devtools");
  return { default: mod.ReactQueryDevtools };
});

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5 * 60 * 1000, // 5 minutes stale time
      gcTime: 10 * 60 * 1000, // 10 minutes cache garbage collection time
      retry: 1,
      refetchOnWindowFocus: false, // Prevent excessive refetching
    },
    mutations: {
      retry: 1,
    },
  },
});

export function clearQueryCache(): void {
  queryClient.clear();
}

export function shouldRenderQueryDevtools(): boolean {
  return shouldEnableDevelopmentDiagnostics();
}

export function QueryProvider({ children }: { children: React.ReactNode }) {
  return (
    <QueryClientProvider client={queryClient}>
      {children}
      {shouldRenderQueryDevtools() && (
        <Suspense fallback={null}>
          <ReactQueryDevtools
            initialIsOpen={false}
            buttonPosition="bottom-left"
          />
        </Suspense>
      )}
    </QueryClientProvider>
  );
}
