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
      staleTime: 60 * 1000, // 1 minute
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
