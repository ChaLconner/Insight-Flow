import { useQuery } from '@tanstack/react-query';
import { dashboardApi } from '@/lib/api-endpoints';
import type { RecentActivity } from '@/types';

// Static colors array - defined outside to prevent recreation
const PROJECT_COLORS = ["#6366f1", "#10b981", "#f59e0b", "#ef4444", "#8b5cf6"] as const;

// Type definitions for dashboard data
export interface DashboardStats {
    totalProjects: number;
    totalProjectsChange?: string;
    totalProjectsTrend?: 'up' | 'down';
    totalTasks: number;
    completedTasks: number;
    inProgressTasks: number;
    inProgressTasksChange?: string;
    inProgressTasksTrend?: 'up' | 'down';
    pendingReviewTasks: number;
    pendingReviewTasksChange?: string;
    pendingReviewTasksTrend?: 'up' | 'down';
    teamVelocity: number;
    teamVelocityChange?: string;
    teamVelocityTrend?: 'up' | 'down';
}

export interface DashboardProject {
    id: string;
    name: string;
    description?: string | null;
    progress: number;
    color: string;
    status?: 'active' | 'archived' | 'suspended';
    updated_at?: string;
}

export interface DashboardData {
    stats: DashboardStats;
    recentProjects: DashboardProject[];
    recentActivities: RecentActivity[];
}

// Query key factory for dashboard queries
export const dashboardKeys = {
    all: ['dashboard'] as const,
    overview: () => [...dashboardKeys.all, 'overview'] as const,
};

export function useDashboard() {
    return useQuery({
        queryKey: dashboardKeys.overview(),
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
            const recentProjects: DashboardProject[] = (data.recentProjects || []).map((p, index) => ({
                id: p.id,
                name: p.name,
                description: p.description,
                progress: p.progress ?? 0,
                color: p.color && p.color !== '#6366f1'
                    ? p.color
                    : PROJECT_COLORS[index % PROJECT_COLORS.length],
                status: (p.status as 'active' | 'archived' | 'suspended') || 'active',
            }));

            return {
                stats,
                recentProjects,
                recentActivities: data.recentActivities || [],
            };
        },
        staleTime: 5 * 60 * 1000, // 5 minutes
        gcTime: 10 * 60 * 1000, // 10 minutes (formerly cacheTime)
        refetchOnWindowFocus: true,
        refetchOnMount: false, // Don't refetch if data is fresh
    });
}
