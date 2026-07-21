import { describe, it, expect, vi } from 'vitest';
import { renderHook } from '@testing-library/react';
import { useAnalytics, useTeamWorkload } from '@/hooks/use-analytics';
import { analyticsApi } from '@/lib/api-endpoints';
import React from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

vi.mock('@/lib/api-endpoints', () => ({
  analyticsApi: {
    getAnalytics: vi.fn().mockResolvedValue({ totalTasks: 10 }),
    getTeamWorkload: vi.fn().mockResolvedValue({ items: [] }),
  },
}));

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return ({ children }: { children: React.ReactNode }) => (
    React.createElement(QueryClientProvider, { client: queryClient }, children)
  );
}

describe('useAnalytics hooks', () => {
  it('fetches analytics with enabled true and false', () => {
    const { result: resEnabled } = renderHook(() => useAnalytics('7d', { enabled: true }), {
      wrapper: createWrapper(),
    });
    expect(resEnabled.current).toBeDefined();

    const { result: resDisabled } = renderHook(() => useAnalytics('7d', { enabled: false }), {
      wrapper: createWrapper(),
    });
    expect(resDisabled.current.isPending).toBe(true);
  });

  it('fetches team workload with options', () => {
    const { result } = renderHook(() => useTeamWorkload({ page: 1 }, { enabled: true }), {
      wrapper: createWrapper(),
    });
    expect(result.current).toBeDefined();
  });
});
