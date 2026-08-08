import { useQuery } from "@tanstack/react-query";
import { dashboardApi } from "@/lib/api-endpoints";
import { getProjectColor } from "@/lib/project-utils";
import { useAuthStore } from "@/stores/auth-store";
import type { RecentActivity } from "@/types";

// Type definitions for dashboard data
export interface DashboardStats {
  totalProjects: number;
  totalProjectsChange?: string;
  totalProjectsTrend?: "up" | "down";
  totalTasks: number;
  completedTasks: number;
  inProgressTasks: number;
  inProgressTasksChange?: string;
  inProgressTasksTrend?: "up" | "down";
  pendingReviewTasks: number;
  pendingReviewTasksChange?: string;
  pendingReviewTasksTrend?: "up" | "down";
  teamVelocity: number;
  teamVelocityChange?: string;
  teamVelocityTrend?: "up" | "down";
}

export interface DashboardProject {
  id: string;
  name: string;
  description?: string | null;
  progress: number;
  color: string;
  status?: "active" | "archived" | "suspended";
  updated_at?: string;
}

export interface DashboardData {
  stats: DashboardStats;
  recentProjects: DashboardProject[];
  recentActivities: RecentActivity[];
}

// Query key factory for dashboard queries
export const dashboardKeys = {
  all: ["dashboard"] as const,
  overview: (userId?: string | null) =>
    userId
      ? ([...dashboardKeys.all, "overview", userId] as const)
      : ([...dashboardKeys.all, "overview"] as const),
};

interface UseDashboardOptions {
  enabled?: boolean;
}

export function useDashboard(options: UseDashboardOptions = {}) {
  const userId = useAuthStore((state) => state.user?.id ?? null);

  return useQuery({
    queryKey: dashboardKeys.overview(userId),
    queryFn: async () => {
      const data = await dashboardApi.getOverview();
      return data;
    },
    select: (data): DashboardData => {
      // Transform and normalize data
      const stats: DashboardStats = {
        totalProjects: data.stats.totalProjects ?? 0,
        totalProjectsChange: data.stats.totalProjectsChange,
        totalProjectsTrend: data.stats.totalProjectsTrend,
        totalTasks: data.stats.totalTasks ?? 0,
        completedTasks: data.stats.completedTasks ?? 0,
        inProgressTasks: data.stats.inProgressTasks ?? 0,
        inProgressTasksChange: data.stats.inProgressTasksChange,
        inProgressTasksTrend: data.stats.inProgressTasksTrend,
        pendingReviewTasks: data.stats.pendingReviewTasks ?? 0,
        pendingReviewTasksChange: data.stats.pendingReviewTasksChange,
        pendingReviewTasksTrend: data.stats.pendingReviewTasksTrend,
        teamVelocity: data.stats.teamVelocity ?? 0,
        teamVelocityChange: data.stats.teamVelocityChange,
        teamVelocityTrend: data.stats.teamVelocityTrend,
      };

      // Transform projects with color assignment
      const recentProjects: DashboardProject[] = (
        data.recentProjects || []
      ).map((p, index) => ({
        id: p.id,
        name: p.name,
        description: p.description,
        progress: p.progress ?? 0,
        color: getProjectColor(p.color, index),
        status: (p.status as "active" | "archived" | "suspended") || "active",
      }));

      return {
        stats,
        recentProjects,
        recentActivities: data.recentActivities || [],
      };
    },
    staleTime: 2 * 60 * 1000, // 2 minutes (aligned with backend cache TTL)
    gcTime: 5 * 60 * 1000, // 5 minutes (formerly cacheTime)
    refetchOnWindowFocus: false,
    refetchOnMount: false, // Don't refetch if data is fresh
    enabled: options.enabled ?? true,
  });
}
