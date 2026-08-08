"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { lazy, Suspense, useState } from "react";
import { shouldEnableDevelopmentDiagnostics } from "@/lib/runtime-flags";

const ReactQueryDevtools = lazy(async () => {
  const mod = await import("@tanstack/react-query-devtools");
  return { default: mod.ReactQueryDevtools };
});

function makeQueryClient(): QueryClient {
  return new QueryClient({
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
}

let browserQueryClient: QueryClient | undefined = undefined;

export function getQueryClient(): QueryClient {
  if (typeof window === "undefined") {
    // Server: always make a new query client
    return makeQueryClient();
  } else {
    // Browser: make a new query client if we don't already have one
    browserQueryClient ??= makeQueryClient();
    return browserQueryClient;
  }
}

export function clearQueryCache(): void {
  getQueryClient().clear();
}

export function shouldRenderQueryDevtools(): boolean {
  return shouldEnableDevelopmentDiagnostics();
}

export function QueryProvider({ children }: { children: React.ReactNode }) {
  const [queryClient] = useState(() => getQueryClient());

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
