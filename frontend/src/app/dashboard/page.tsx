"use client";

import { useEffect, useState } from "react";
import { formatDistanceToNow } from "date-fns";
import { ProtectedLayout } from "@/components/layout/ProtectedLayout";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { useAuthStore } from "@/stores/auth-store";
import { dashboardApi } from "@/lib/api-endpoints";
import { getAvatarUrl } from "@/lib/utils";
import {
    Briefcase,
    CheckCircle2,
    Clock,
    TrendingUp,
    MoreHorizontal,
    ArrowUpRight,
    ArrowDownRight,
    Loader2
} from "lucide-react";
import { Skeleton } from "@/components/ui/skeleton";

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

interface RecentProject {
    id: string;
    name: string;
    description?: string;
    progress: number;
    color?: string;
    updated_at?: string;
    status?: string;
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
    recentProjects: RecentProject[];
    recentActivities: RecentActivity[];
}

export default function DashboardPage() {
    const [dashboardData, setDashboardData] = useState<DashboardData | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [dataFetched, setDataFetched] = useState(false);

    // Use auth store instead of direct localStorage access
    const { accessToken, isAuthenticated, isLoading } = useAuthStore();

    useEffect(() => {
        // Fast path: Skip if we're still loading or already have data
        if (isLoading || dataFetched) { return; }

        // Optimized conditions for faster loading
        if (isAuthenticated && accessToken) {
            fetchDashboardData();
        } else if (!isAuthenticated) {
            setError('Please login to view dashboard');
            setLoading(false);
        }
    }, [isAuthenticated, accessToken, isLoading, dataFetched]);

    const fetchDashboardData = async () => {
        try {
            setLoading(true);

            if (!accessToken) {
                setError('No access token found');
                setLoading(false);
                return;
            }

            // Fetch overview and recent projects in parallel for better performance
            const [overviewData, recentProjectsData] = await Promise.all([
                dashboardApi.getOverview(),
                dashboardApi.getRecentProjects()
            ]);

            setDashboardData({
                stats: {
                    ...overviewData.stats,
                    inProgressTasks: 0,
                    pendingReviewTasks: 0,
                    teamVelocity: 0
                },
                recentProjects: (recentProjectsData || []).map(p => ({
                    ...p,
                    progress: 0, // Default progress if missing
                    color: 'blue' // Default color
                })),
                recentActivities: (overviewData.recentActivities as RecentActivity[]) || []
            });

            setError(null);
            setDataFetched(true); // Mark data as fetched to prevent loops
        } catch (err: any) {
            console.error('Error fetching dashboard data:', err);
            if (err.response?.status === 401) {
                setError('Please login again');
            } else {
                setError('Failed to load dashboard data');
            }
        } finally {
            setLoading(false);
        }
    };

    if (loading) {
        return (
            <ProtectedLayout>
                <div className="space-y-8">
                    {/* Welcome Section Skeleton */}
                    <div className="flex items-center justify-between">
                        <div className="space-y-2">
                            <Skeleton className="h-8 w-48" />
                            <Skeleton className="h-4 w-64" />
                        </div>
                        <div className="flex gap-3">
                            <Skeleton className="h-10 w-28" />
                            <Skeleton className="h-10 w-32" />
                        </div>
                    </div>

                    {/* Stats Grid Skeleton */}
                    <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
                        {[...Array(4)].map((_, i) => (
                            <Card key={i} className="border-white/10 bg-white/5 backdrop-blur-sm">
                                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                                    <Skeleton className="h-4 w-24" />
                                    <Skeleton className="h-8 w-8 rounded-lg" />
                                </CardHeader>
                                <CardContent>
                                    <Skeleton className="h-8 w-16 mb-2" />
                                    <Skeleton className="h-3 w-32" />
                                </CardContent>
                            </Card>
                        ))}
                    </div>

                    {/* Recent Projects & Activity Skeleton */}
                    <div className="grid gap-8 lg:grid-cols-7">
                        {/* Projects List Skeleton */}
                        <Card className="col-span-4 border-white/10 bg-white/5 backdrop-blur-sm">
                            <CardHeader className="flex flex-row items-center justify-between">
                                <Skeleton className="h-6 w-32" />
                                <Skeleton className="h-5 w-5 rounded-full" />
                            </CardHeader>
                            <CardContent>
                                <div className="space-y-6">
                                    {[...Array(3)].map((_, i) => (
                                        <div key={i} className="flex items-center justify-between">
                                            <div className="flex items-center gap-4">
                                                <Skeleton className="h-10 w-10 rounded-lg" />
                                                <div className="space-y-2">
                                                    <Skeleton className="h-4 w-32" />
                                                    <Skeleton className="h-3 w-48" />
                                                </div>
                                            </div>
                                            <div className="flex items-center gap-4">
                                                <div className="hidden sm:block space-y-2">
                                                    <Skeleton className="h-3 w-8 ml-auto" />
                                                    <Skeleton className="h-1.5 w-24 rounded-full" />
                                                </div>
                                                <Skeleton className="h-5 w-16 rounded-full" />
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            </CardContent>
                        </Card>

                        {/* Activity Feed Skeleton */}
                        <Card className="col-span-3 border-white/10 bg-white/5 backdrop-blur-sm">
                            <CardHeader>
                                <Skeleton className="h-6 w-32" />
                            </CardHeader>
                            <CardContent>
                                <div className="space-y-8">
                                    {[...Array(4)].map((_, i) => (
                                        <div key={i} className="flex gap-4">
                                            <Skeleton className="h-8 w-8 rounded-full" />
                                            <div className="space-y-2 flex-1">
                                                <Skeleton className="h-4 w-full" />
                                                <Skeleton className="h-3 w-24" />
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            </CardContent>
                        </Card>
                    </div>
                </div>
            </ProtectedLayout>
        );
    }

    if (error) {
        return (
            <ProtectedLayout>
                <div className="flex items-center justify-center h-64">
                    <div className="text-red-400">{error}</div>
                </div>
            </ProtectedLayout>
        );
    }

    if (!dashboardData) { return null; }

    const { stats, recentProjects, recentActivities } = dashboardData;

    return (
        <ProtectedLayout>
            <div className="space-y-8">
                {/* Welcome Section */}
                <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
                    <div>
                        <h2 className="text-3xl font-bold tracking-tight text-white">Dashboard</h2>
                        <p className="text-zinc-400">Here's an overview of your projects and tasks.</p>
                    </div>
                    <div className="flex items-center gap-2">
                        <Badge variant="outline" className="bg-emerald-500/10 text-emerald-500 border-emerald-500/20 px-3 py-1">
                            <span className="w-2 h-2 rounded-full bg-emerald-500 mr-2 animate-pulse" />
                            System Online
                        </Badge>
                    </div>
                </div>

                {/* Stats Grid */}
                <div className="grid grid-cols-2 gap-4 md:grid-cols-2 lg:grid-cols-4">
                    {[
                        {
                            title: "Total Projects",
                            value: stats.totalProjects.toString(),
                            change: "+2.5%",
                            trend: "up" as const,
                            icon: Briefcase,
                            color: "text-blue-400",
                            bg: "bg-blue-400/10",
                        },
                        {
                            title: "Active Tasks",
                            value: (stats.inProgressTasks || 0).toString(),
                            change: "+12%",
                            trend: "up" as const,
                            icon: CheckCircle2,
                            color: "text-emerald-400",
                            bg: "bg-emerald-400/10",
                        },
                        {
                            title: "Pending Review",
                            value: (stats.pendingReviewTasks || 0).toString(),
                            change: "-5%",
                            trend: "down" as const,
                            icon: Clock,
                            color: "text-amber-400",
                            bg: "bg-amber-400/10",
                        },
                        {
                            title: "Team Velocity",
                            value: `${stats.teamVelocity || 0}%`,
                            change: "+8%",
                            trend: "up" as const,
                            icon: TrendingUp,
                            color: "text-violet-400",
                            bg: "bg-violet-400/10",
                        },
                    ].map((stat, index) => (
                        <Card key={index} className="border-white/10 bg-white/5 backdrop-blur-sm hover:bg-white/10 transition-colors">
                            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                                <CardTitle className="text-sm font-medium text-zinc-400">
                                    {stat.title}
                                </CardTitle>
                                <div className={`rounded-lg p-2 ${stat.bg}`}>
                                    <stat.icon className={`h-4 w-4 ${stat.color}`} />
                                </div>
                            </CardHeader>
                            <CardContent>
                                <div className="text-2xl font-bold text-white">{stat.value}</div>
                                <div className="flex items-center gap-2 mt-1">
                                    <span className={`flex items-center text-xs ${stat.trend === 'up' ? 'text-emerald-400' : 'text-red-400'}`}>
                                        {stat.trend === 'up' ? <ArrowUpRight className="h-3 w-3 mr-1" /> : <ArrowDownRight className="h-3 w-3 mr-1" />}
                                        {stat.change}
                                    </span>
                                    <span className="text-xs text-zinc-500">from last month</span>
                                </div>
                            </CardContent>
                        </Card>
                    ))}
                </div>

                {/* Recent Projects & Activity */}
                <div className="grid gap-8 lg:grid-cols-7">
                    {/* Projects List */}
                    <Card className="col-span-4 border-white/10 bg-white/5 backdrop-blur-sm">
                        <CardHeader className="flex flex-row items-center justify-between">
                            <CardTitle className="text-lg font-semibold text-white">Recent Projects</CardTitle>
                            <Button variant="ghost" size="sm" className="text-zinc-400 hover:text-white" asChild>
                                <a href="/projects">View All</a>
                            </Button>
                        </CardHeader>
                        <CardContent>
                            <div className="space-y-4">
                                {recentProjects.length > 0 ? recentProjects.map((project, i) => (
                                    <div key={project.id} className="group p-3 rounded-xl hover:bg-white/5 transition-all border border-transparent hover:border-white/5">
                                        <div className="flex flex-col sm:flex-row sm:items-center gap-4">
                                            {/* Icon & Title */}
                                            <div className="grid grid-cols-[auto_minmax(0,1fr)] gap-4 w-full sm:w-auto sm:flex-1 items-center">
                                                <div className={`h-12 w-12 rounded-xl flex items-center justify-center shadow-lg transition-transform group-hover:scale-105 duration-300 shrink-0`} style={{ backgroundColor: project.color }}>
                                                    <span className="font-bold text-white text-lg">
                                                        {project.name && typeof project.name === 'string' ? project.name[0] : ''}
                                                    </span>
                                                </div>
                                                <div className="min-w-0 overflow-hidden w-full">
                                                    <h4 className="font-semibold text-white text-base truncate group-hover:text-indigo-400 transition-colors">
                                                        {project.name}
                                                    </h4>
                                                    <p className="text-sm text-zinc-400 truncate">
                                                        {project.description || 'No description'}
                                                    </p>
                                                </div>
                                            </div>

                                            {/* Status & Progress */}
                                            <div className="flex items-center justify-between sm:justify-end gap-4 w-full sm:w-auto mt-2 sm:mt-0">
                                                <div className="flex-1 sm:flex-none sm:w-32">
                                                    <div className="flex justify-between text-xs mb-1.5">
                                                        <span className="text-zinc-400">Progress</span>
                                                        <span className="text-white font-medium">{project.progress}%</span>
                                                    </div>
                                                    <div className="h-1.5 w-full rounded-full bg-white/10 overflow-hidden">
                                                        <div
                                                            className="h-full rounded-full transition-all duration-500"
                                                            style={{ width: `${project.progress}%`, backgroundColor: project.color }}
                                                        />
                                                    </div>
                                                </div>
                                                <Badge variant="secondary" className="bg-white/10 text-zinc-300 hover:bg-white/20 shrink-0">
                                                    Active
                                                </Badge>
                                            </div>
                                        </div>
                                    </div>
                                )) : (
                                    <div className="text-center text-zinc-400 py-12">
                                        <div className="mx-auto h-12 w-12 rounded-full bg-white/5 flex items-center justify-center mb-3">
                                            <Briefcase className="h-6 w-6 text-zinc-500" />
                                        </div>
                                        <p className="font-medium text-white">No projects yet</p>
                                        <p className="text-sm mt-1">Create your first project to get started!</p>
                                    </div>
                                )}
                            </div>
                        </CardContent>
                    </Card>

                    {/* Activity Feed */}
                    <Card className="col-span-3 border-white/10 bg-white/5 backdrop-blur-sm">
                        <CardHeader>
                            <CardTitle className="text-lg font-semibold text-white">Recent Activity</CardTitle>
                        </CardHeader>
                        <CardContent>
                            <div className="space-y-8">
                                {recentActivities.length > 0 ? recentActivities.map((activity, i) => (
                                    <div key={activity.id} className="flex gap-4">
                                        <div className="relative">
                                            <div className="h-8 w-8 rounded-full bg-zinc-800 border border-white/10 flex items-center justify-center overflow-hidden shrink-0 group">
                                                {activity.user.avatar ? (
                                                    <img
                                                        src={getAvatarUrl(activity.user.avatar)}
                                                        alt={activity.user.name}
                                                        className="h-full w-full object-cover"
                                                        onError={(e) => {
                                                            e.currentTarget.style.display = 'none';
                                                            e.currentTarget.nextElementSibling?.classList.remove('hidden');
                                                        }}
                                                    />
                                                ) : null}
                                                <span className={`${activity.user.avatar ? 'hidden' : ''} text-xs font-medium text-zinc-400`}>
                                                    {activity.user.name && typeof activity.user.name === 'string'
                                                        ? activity.user.name.split(' ').map(n => n[0]).join('').toUpperCase()
                                                        : ''}
                                                </span>
                                            </div>
                                            {i !== recentActivities.length - 1 && (
                                                <div className="absolute left-4 top-8 h-full w-px bg-white/10" />
                                            )}
                                        </div>
                                        <div className="space-y-1">
                                            <p className="text-sm text-zinc-300">
                                                <span className="font-medium text-white">{activity.user.name}</span>{" "}
                                                {activity.action}{" "}
                                                <span className="text-indigo-400">{activity.target}</span>
                                            </p>
                                            <p className="text-xs text-zinc-500">
                                                {activity.timestamp ? formatDistanceToNow(new Date(activity.timestamp), { addSuffix: true }) : ''}
                                            </p>
                                        </div>
                                    </div>
                                )) : (
                                    <div className="text-center text-zinc-400 py-8">
                                        No recent activity
                                    </div>
                                )}
                            </div>
                        </CardContent>
                    </Card>
                </div>
            </div>
        </ProtectedLayout>
    );
}
