import { create } from 'zustand';
import { dashboardApi } from '@/lib/api-endpoints';
import { Project, Task } from '@/types';

interface DashboardStats {
    totalProjects: number;
    totalTasks: number;
    completedTasks: number;
    pendingTasks: number;
    teamMembers: number;
    inProgressTasks?: number;
    pendingReviewTasks?: number;
    teamVelocity?: number;
}

interface RecentActivity {
    id: string;
    user: { name: string; id: string; avatar?: string };
    action: string;
    target: string;
    timestamp: string;
}

interface DashboardData {
    stats: DashboardStats;
    recentProjects: Project[];
    recentActivities: RecentActivity[];
}

interface DashboardState {
    data: DashboardData | null;
    isLoading: boolean;
    error: string | null;
    lastFetched: number | null;

    // Actions
    fetchDashboardData: (force?: boolean) => Promise<void>;
    reset: () => void;
}

export const useDashboardStore = create<DashboardState>((set, get) => ({
    data: null,
    isLoading: false,
    error: null,
    lastFetched: null,

    fetchDashboardData: async (force = false) => {
        const { data, lastFetched, isLoading } = get();

        // Cache validity check (e.g., 5 minutes)
        const now = Date.now();
        const isCacheValid = lastFetched && (now - lastFetched < 5 * 60 * 1000);

        if (!force && data && isCacheValid) {
            return;
        }

        if (isLoading) return;

        set({ isLoading: true, error: null });

        try {
            // Fetch overview and recent projects in parallel
            const [overviewData, recentProjectsData] = await Promise.all([
                dashboardApi.getOverview(),
                dashboardApi.getRecentProjects()
            ]);

            const formattedData: DashboardData = {
                stats: {
                    ...overviewData.stats,
                    // Ensure defaults for optional fields if missing from API
                    inProgressTasks: overviewData.stats.inProgressTasks ?? 0,
                    pendingReviewTasks: overviewData.stats.pendingReviewTasks ?? 0,
                    teamVelocity: overviewData.stats.teamVelocity ?? 0
                },
                recentProjects: (recentProjectsData || []).map(p => ({
                    ...p,
                    progress: p.progress ?? 0,
                    color: p.color || '#6366f1'
                })),
                recentActivities: (overviewData.recentActivities as RecentActivity[]) || []
            };

            set({
                data: formattedData,
                lastFetched: now,
                isLoading: false
            });
        } catch (error: any) {
            console.error('Dashboard store: Error fetching data', error);
            set({
                error: error.message || 'Failed to fetch dashboard data',
                isLoading: false
            });
        }
    },

    reset: () => set({ data: null, lastFetched: null, error: null })
}));
