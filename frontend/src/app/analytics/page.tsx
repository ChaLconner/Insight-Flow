"use client";

import { useState, useMemo, useCallback } from "react";
import dynamic from "next/dynamic";
import { ProtectedLayout } from "@/components/layout/ProtectedLayout";
import { AnalyticsPeriod } from "@/types";
import { useAnalytics, useTeamWorkload } from "@/hooks/use-analytics";
import type { TeamWorkloadParams } from "@/app/analytics/types";
import { useAuthStore } from "@/stores/auth-store";

// Components
import { AnalyticsHeader } from "@/components/analytics/AnalyticsHeader";
import { KeyMetrics } from "@/components/analytics/KeyMetrics";
// ChartCarousel is now lazy loaded
import { AnalyticsError } from "@/components/analytics/AnalyticsError";
import {
  AnalyticsPageSkeleton,
  PerformanceTrendsSkeleton,
  ListSkeleton,
  ChartCarouselSkeleton,
} from "@/components/analytics/AnalyticsSkeletons";

// ============================================
// Lazy loaded components (below the fold)
// ============================================
const PerformanceTrends = dynamic(
  () =>
    import("@/components/analytics/PerformanceTrends").then((mod) => ({
      default: mod.PerformanceTrends,
    })),
  {
    loading: () => <PerformanceTrendsSkeleton />,
    ssr: false,
  },
);

const ChartCarousel = dynamic(
  () =>
    import("@/components/analytics/ChartCarousel").then((mod) => ({
      default: mod.ChartCarousel,
    })),
  {
    loading: () => <ChartCarouselSkeleton />,
    ssr: false,
  },
);

const ProjectList = dynamic(
  () =>
    import("@/components/analytics/ProjectList").then((mod) => ({
      default: mod.ProjectList,
    })),
  {
    loading: () => <ListSkeleton title="Project Performance" />,
    ssr: false,
  },
);

const TeamList = dynamic(
  () =>
    import("@/components/analytics/TeamList").then((mod) => ({
      default: mod.TeamList,
    })),
  {
    loading: () => <ListSkeleton title="Team Performance" />,
    ssr: false,
  },
);

// ============================================
// Constants
// ============================================
const INITIAL_WORKLOAD_PARAMS: TeamWorkloadParams = {
  page: 1,
  pageSize: 10,
  sortBy: "tasks",
  sortOrder: "desc",
} as const;

const PAGINATION_THRESHOLD = 10;
const EMPTY_ARRAY: never[] = [];

// ============================================
// Main Component
// ============================================
export default function AnalyticsPage() {
  const authLoading = useAuthStore((state) => state.isLoading);
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated);
  const isInitialized = useAuthStore((state) => state.isInitialized);
  const canFetchAnalytics = isInitialized && isAuthenticated;

  // State
  const [selectedPeriod, setSelectedPeriod] = useState<AnalyticsPeriod>(
    AnalyticsPeriod.MONTH,
  );
  const [workloadParams, setWorkloadParams] = useState<TeamWorkloadParams>(
    INITIAL_WORKLOAD_PARAMS,
  );

  // Data fetching hooks
  const { data, isLoading, error, refetch, isRefetching } =
    useAnalytics(selectedPeriod, { enabled: canFetchAnalytics });
  const shouldFetchPaginatedWorkload =
    (data?.teamWorkload?.length ?? 0) >= PAGINATION_THRESHOLD;

  const {
    data: paginatedWorkload,
    isLoading: isWorkloadLoading,
    isFetching: isWorkloadFetching,
  } = useTeamWorkload(workloadParams, {
    enabled: canFetchAnalytics && shouldFetchPaginatedWorkload,
  });

  // ============================================
  // Memoized values
  // ============================================

  // Check if we should use paginated mode
  const usePaginatedWorkload = useMemo(() => {
    const paginatedTotal = paginatedWorkload?.total ?? 0;
    return shouldFetchPaginatedWorkload || paginatedTotal > PAGINATION_THRESHOLD;
  }, [paginatedWorkload?.total, shouldFetchPaginatedWorkload]);

  // Combined loading state for workload
  const isWorkloadBusy = isWorkloadLoading || isWorkloadFetching;

  // ============================================
  // Callbacks
  // ============================================

  const handleRefresh = useCallback(() => {
    refetch();
  }, [refetch]);

  const handleWorkloadPageChange = useCallback((params: TeamWorkloadParams) => {
    setWorkloadParams(params);
  }, []);

  const handleRetry = useCallback(() => {
    refetch();
  }, [refetch]);

  // ============================================
  // Render logic
  // ============================================

  // Loading state
  if (authLoading || !canFetchAnalytics || isLoading) {
    return (
      <ProtectedLayout>
        <AnalyticsPageSkeleton />
      </ProtectedLayout>
    );
  }

  // Error state
  // eslint-disable-next-line @typescript-eslint/prefer-nullish-coalescing
  if (error || !data) {
    return <AnalyticsError error={error} onRetry={handleRetry} />;
  }

  // Success state
  return (
    <ProtectedLayout>
      <div className="space-y-8">
        {/* Above the fold - critical content */}
        <AnalyticsHeader
          onRefresh={handleRefresh}
          isRefetching={isRefetching}
        />

        {data.overview && (
          <KeyMetrics
            data={data.overview}
            period={selectedPeriod}
            trends={data.trends ?? EMPTY_ARRAY}
          />
        )}

        <div className="mb-12">
          <ChartCarousel
            burndownData={data.weeklyBurndown ?? EMPTY_ARRAY}
            workloadData={data.teamWorkload ?? EMPTY_ARRAY}
            dailyTrendsData={data.dailyTrends ?? EMPTY_ARRAY}
            statusDistribution={data.statusDistribution ?? EMPTY_ARRAY}
            priorityDistribution={data.priorityDistribution ?? EMPTY_ARRAY}
            period={selectedPeriod}
            setPeriod={setSelectedPeriod}
            usePaginatedWorkload={usePaginatedWorkload}
            paginatedWorkloadData={paginatedWorkload}
            onWorkloadPageChange={handleWorkloadPageChange}
            isWorkloadLoading={isWorkloadBusy}
          />
        </div>

        {/* Below the fold - lazy loaded */}
        <PerformanceTrends trends={data.trends ?? EMPTY_ARRAY} />

        <div className="grid gap-8 lg:grid-cols-2">
          <ProjectList projects={data.projects ?? EMPTY_ARRAY} />
          <TeamList team={data.team ?? EMPTY_ARRAY} />
        </div>
      </div>
    </ProtectedLayout>
  );
}
