import { useQuery } from '@tanstack/react-query';
import { dashboardApi } from '@/lib/api-endpoints';
import { Project } from '@/types';

const PROJECT_COLORS = ["#6366f1", "#10b981", "#f59e0b", "#ef4444", "#8b5cf6"];

export function useDashboard() {
    return useQuery({
        queryKey: ['dashboard', 'overview'],
        queryFn: async () => {
            const data = await dashboardApi.getOverview();
            return data;
        },
        select: (data) => {
            return {
                ...data,
                stats: {
                    ...data.stats,
                    inProgressTasks: data.stats.inProgressTasks ?? 0,
                    pendingReviewTasks: data.stats.pendingReviewTasks ?? 0,
                    teamVelocity: data.stats.teamVelocity ?? 0
                },
                recentProjects: (data.recentProjects as Project[] || []).map((p, index) => ({
                    ...p,
                    progress: p.progress ?? 0,
                    color: p.color && p.color !== '#6366f1' ? p.color : PROJECT_COLORS[index % PROJECT_COLORS.length]
                })),
                recentActivities: data.recentActivities || []
            };
        },
        staleTime: 5 * 60 * 1000, // 5 minutes
        refetchOnWindowFocus: true,
    });
}
