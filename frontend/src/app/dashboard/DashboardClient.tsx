"use client";

import { useMemo, useCallback, useRef, Suspense } from "react";
import { ProtectedLayout } from "@/components/layout/ProtectedLayout";
import { useAuthStore } from "@/stores/auth-store";
import { useDashboard } from "@/hooks/use-dashboard";
import { ErrorBoundary } from "@/components/error-boundary";
import { useQueryClient } from "@tanstack/react-query";
import { dashboardKeys } from "@/hooks/use-dashboard";

import dynamic from "next/dynamic";
import { DashboardHeader } from "./components/DashboardHeader";
import { DashboardSkeleton } from "./components/DashboardSkeleton";
import { DashboardError } from "./components/DashboardError";

// Lazy load components to reduce initial bundle size
import { DashboardStats } from "./components/DashboardStats";
import {
  ProjectsListSkeleton,
  ActivityFeedSkeleton,
  StatsGridSkeleton,
} from "./components/DashboardSkeleton";

// Lazy load components to reduce initial bundle size
const RecentProjects = dynamic(
  () => import("./components/RecentProjects").then((mod) => mod.RecentProjects),
  {
    loading: () => <ProjectsListSkeleton />,
  },
);
const RecentActivity = dynamic(
  () => import("./components/RecentActivity").then((mod) => mod.RecentActivity),
  {
    loading: () => <ActivityFeedSkeleton />,
  },
);

import type { DashboardStatsData } from "./components";
import type { ProjectCardProject } from "./components";
import type { ActivityItemData } from "./components";
import {
  isEditableEventTarget,
  useDocumentKeyDown,
} from "@/hooks/use-keyboard-shortcuts";

const EMPTY_ARRAY: never[] = [];

// Keyboard shortcut constants
const KEYBOARD_SHORTCUTS = {
  REFRESH: "r",
  FOCUS_SEARCH: "/",
} as const;

export default function DashboardClient() {
  const { isLoading: authLoading } = useAuthStore();
  const queryClient = useQueryClient();
  const { data, isLoading, error, refetch, isFetching } =
    useDashboard();
  const announcerRef = useRef<HTMLDivElement>(null);

  const loading = authLoading || (isLoading && !data);

  // Announce function for screen readers
  const announce = useCallback((message: string) => {
    if (announcerRef.current) {
      announcerRef.current.textContent = message;
    }
  }, []);

  // Refresh handler
  const handleRefresh = useCallback(() => {
    announce("Refreshing dashboard data...");
    refetch()
      .then(() => {
        announce("Dashboard data refreshed successfully.");
      })
      .catch(() => {
        announce("Failed to refresh dashboard data.");
      });
  }, [refetch, announce]);

  // Retry handler for error state
  const handleRetry = useCallback(() => {
    queryClient.invalidateQueries({ queryKey: dashboardKeys.overview() });
    refetch();
  }, [queryClient, refetch]);

  const handleKeyboardShortcut = useCallback(
    (event: KeyboardEvent) => {
      if (isEditableEventTarget(event.target)) {
        return;
      }

      if (
        event.key.toLowerCase() === KEYBOARD_SHORTCUTS.REFRESH &&
        !event.ctrlKey &&
        !event.metaKey
      ) {
        event.preventDefault();
        handleRefresh();
      }
    },
    [handleRefresh],
  );
  useDocumentKeyDown(handleKeyboardShortcut);

  // Memoize transformed data to prevent unnecessary re-renders
  const statsData = useMemo<DashboardStatsData>(() => {
    if (!data?.stats) {
      return {
        totalProjects: 0,
        totalProjectsChange: "+0%",
        totalProjectsTrend: "up",
        inProgressTasks: 0,
        inProgressTasksChange: "+0%",
        inProgressTasksTrend: "up",
        pendingReviewTasks: 0,
        pendingReviewTasksChange: "+0%",
        pendingReviewTasksTrend: "up",
        teamVelocity: 0,
        teamVelocityChange: "+0%",
        teamVelocityTrend: "up",
      };
    }
    return data.stats;
  }, [data?.stats]);

  const projectsData = useMemo<ProjectCardProject[]>(() => {
    if (!data?.recentProjects) {
      return EMPTY_ARRAY;
    }
    // Limit to 6 projects to prevent hydration blocking
    return data.recentProjects.slice(0, 6).map((project) => ({
      id: project.id,
      name: project.name,
      description: project.description,
      progress: project.progress,
      color: project.color,
      status: project.status as "active" | "archived" | "suspended" | undefined,
    }));
  }, [data?.recentProjects]);

  const activitiesData = useMemo<ActivityItemData[]>(() => {
    if (!data?.recentActivities) {
      return EMPTY_ARRAY;
    }
    // Limit to 10 activities to prevent hydration blocking
    return data.recentActivities.slice(0, 10);
  }, [data?.recentActivities]);

  // Calculate last updated time
  /* const lastUpdated = useMemo(() => {
    return dataUpdatedAt ? new Date(dataUpdatedAt) : null;
  }, [dataUpdatedAt]); */

  // Loading state
  if (loading) {
    return (
      <ProtectedLayout>
        <DashboardSkeleton />
      </ProtectedLayout>
    );
  }

  // Error state
  if (error && !data) {
    return (
      <ProtectedLayout>
        <DashboardError
          error={error}
          onRetry={handleRetry}
          isRetrying={isFetching}
        />
      </ProtectedLayout>
    );
  }

  // No data state
  if (!data) {
    return null;
  }

  return (
    <ProtectedLayout>
      <ErrorBoundary>
        {/* Screen reader announcer for dynamic content */}
        <div
          ref={announcerRef}
          role="status"
          aria-live="polite"
          aria-atomic="true"
          className="sr-only"
        />

        {/* Keyboard shortcuts help (hidden, for screen readers) */}
        <div className="sr-only" aria-label="Keyboard shortcuts available">
          Press R to refresh dashboard.
        </div>

        <main id="main-content" className="space-y-8">
          {/* Welcome Section with Refresh and Quick Actions */}
          <DashboardHeader />

          {/* Background refetch indicator */}
          {isFetching && data && (
            <div className="flex items-center justify-center py-2">
              <div className="flex items-center gap-2 text-sm text-zinc-400 bg-white/5 px-4 py-2 rounded-full">
                <div className="w-2 h-2 rounded-full bg-indigo-500 animate-pulse" />
                Updating...
              </div>
            </div>
          )}

          {/* Stats Grid - wrapped in Suspense for streaming */}
          <section aria-label="Dashboard statistics">
            <Suspense fallback={<StatsGridSkeleton />}>
              <DashboardStats stats={statsData} />
            </Suspense>
          </section>

          {/* Recent Projects & Activity - each wrapped in Suspense for parallel streaming */}
          <section aria-label="Recent projects and activity">
            <div className="grid gap-8 lg:grid-cols-7">
              <div className="col-span-full lg:col-span-4">
                <Suspense fallback={<ProjectsListSkeleton />}>
                  <RecentProjects projects={projectsData} />
                </Suspense>
              </div>
              <div className="col-span-full lg:col-span-3">
                <Suspense fallback={<ActivityFeedSkeleton />}>
                  <RecentActivity activities={activitiesData} />
                </Suspense>
              </div>
            </div>
          </section>
        </main>
      </ErrorBoundary>
    </ProtectedLayout>
  );
}
