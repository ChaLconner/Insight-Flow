"use client";

import { useEffect, useState } from "react";
import { ProtectedLayout } from "@/components/layout/ProtectedLayout";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { useAuthStore } from "@/stores/auth-store";
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

interface DashboardStats {
  totalProjects: number;
  totalTasks: number;
  completedTasks: number;
  inProgressTasks: number;
  pendingReviewTasks: number;
  teamVelocity: number;
}

interface RecentProject {
  id: string;
  name: string;
  description: string;
  progress: number;
  color: string;
  updated_at?: string;
}

interface RecentActivity {
  id: string;
  user: { name: string; id: string };
  action: string;
  target: string;
  timestamp: string;
}

interface DashboardData {
  stats: DashboardStats;
  recentProjects: RecentProject[];
  recentActivities: RecentActivity[];
}

export default function Home() {
  const [dashboardData, setDashboardData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [dataFetched, setDataFetched] = useState(false);
  
  // Use auth store instead of direct localStorage access
  const { accessToken, isAuthenticated, isLoading } = useAuthStore();

  useEffect(() => {
    // Fast path: Skip if we're still loading or already have data
    if (isLoading || dataFetched) return;
    
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

      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/dashboard/overview`, {
        headers: {
          'Authorization': `Bearer ${accessToken}`,
          'Content-Type': 'application/json'
        }
      });

      if (!response.ok) {
        if (response.status === 401) {
          setError('Please login again');
          return;
        }
        throw new Error(`Failed to fetch dashboard data: ${response.statusText}`);
      }

      const data = await response.json();
      setDashboardData(data);
      setError(null);
      setDataFetched(true); // Mark data as fetched to prevent loops
    } catch (err) {
      console.error('Error fetching dashboard data:', err);
      setError('Failed to load dashboard data');
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <ProtectedLayout>
        <div className="flex items-center justify-center h-64">
          <Loader2 className="h-8 w-8 animate-spin text-white" />
          <span className="ml-2 text-white">Loading dashboard...</span>
        </div>
      </ProtectedLayout>
    );
  }

  if (error) {
    return (
      <ProtectedLayout>
        <div className="flex flex-col items-center justify-center h-64 space-y-4">
          <div className="text-red-40 text-center">
            <p className="text-lg font-medium">{error}</p>
            <button
              onClick={fetchDashboardData}
              className="mt-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg transition-colors"
            >
              Retry
            </button>
          </div>
        </div>
      </ProtectedLayout>
    );
  }

  if (!dashboardData) {
    return (
      <ProtectedLayout>
        <div className="text-center text-zinc-400 py-8">
          No dashboard data available
        </div>
      </ProtectedLayout>
    );
  }

  const { stats, recentProjects, recentActivities } = dashboardData;

  return (
    <ProtectedLayout>
      <div className="space-y-8">
        {/* Welcome Section */}
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-3xl font-bold tracking-tight text-white">Overview</h2>
            <p className="mt-1 text-zinc-400">Here's what's happening with your projects today.</p>
          </div>
          <div className="flex gap-3">
            <button 
              onClick={fetchDashboardData}
              className="rounded-lg bg-white/5 px-4 py-2 text-sm font-medium text-white hover:bg-white/10 transition-colors"
            >
              Refresh Data
            </button>
            <button className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-500 transition-colors shadow-lg shadow-indigo-500/20">
              New Project
            </button>
          </div>
        </div>

        {/* Stats Grid */}
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          {[
            {
              title: "Total Projects",
              value: stats.totalProjects.toString(),
              change: stats.totalProjects > 0 ? "+2.5%" : "0%",
              trend: stats.totalProjects > 0 ? "up" as const : "down" as const,
              icon: Briefcase,
              color: "text-blue-400",
              bg: "bg-blue-400/10",
            },
            {
              title: "Active Tasks",
              value: stats.inProgressTasks.toString(),
              change: stats.inProgressTasks > 0 ? "+12%" : "0%",
              trend: stats.inProgressTasks > 0 ? "up" as const : "down" as const,
              icon: CheckCircle2,
              color: "text-emerald-400",
              bg: "bg-emerald-400/10",
            },
            {
              title: "Pending Review",
              value: stats.pendingReviewTasks.toString(),
              change: stats.pendingReviewTasks > 0 ? "-5%" : "0%",
              trend: stats.pendingReviewTasks > 0 ? "down" as const : "up" as const,
              icon: Clock,
              color: "text-amber-400",
              bg: "bg-amber-400/10",
            },
            {
              title: "Team Velocity",
              value: `${stats.teamVelocity}%`,
              change: stats.teamVelocity > 50 ? "+8%" : "-3%",
              trend: stats.teamVelocity > 50 ? "up" as const : "down" as const,
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
              <MoreHorizontal className="h-5 w-5 text-zinc-500 cursor-pointer hover:text-white" />
            </CardHeader>
            <CardContent>
              <div className="space-y-6">
                {recentProjects.length > 0 ? recentProjects.map((project, i) => (
                  <div key={project.id} className="flex items-center justify-between group">
                    <div className="flex items-center gap-4">
                      <div className={`h-10 w-10 rounded-lg flex items-center justify-center shadow-lg opacity-80 group-hover:opacity-100 transition-opacity`} style={{ backgroundColor: project.color }}>
                        <span className="font-bold text-white">
                          {project.name && typeof project.name === 'string' ? project.name[0] : ''}
                        </span>
                      </div>
                      <div>
                        <h4 className="font-medium text-white group-hover:text-indigo-400 transition-colors">{project.name}</h4>
                        <p className="text-sm text-zinc-500">{project.description || 'No description'}</p>
                      </div>
                    </div>
                    <div className="flex items-center gap-4">
                      <div className="text-right hidden sm:block">
                        <span className="text-sm font-medium text-zinc-300">{project.progress}%</span>
                        <div className="h-1.5 w-24 rounded-full bg-white/10 mt-1">
                          <div
                            className="h-full rounded-full"
                            style={{ width: `${project.progress}%`, backgroundColor: project.color }}
                          />
                        </div>
                      </div>
                      <Badge variant="secondary" className="bg-white/10 text-zinc-300 hover:bg-white/20">
                        Active
                      </Badge>
                    </div>
                  </div>
                )) : (
                  <div className="text-center text-zinc-400 py-8">
                    No projects found. Create your first project to get started!
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
                      <div className="h-8 w-8 rounded-full bg-zinc-800 border border-white/10 flex items-center justify-center text-xs font-medium text-zinc-400">
                        {activity.user.name && typeof activity.user.name === 'string'
                          ? activity.user.name.split(' ').map(n => n[0]).join('').toUpperCase()
                          : ''}
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
                      <p className="text-xs text-zinc-500">{activity.timestamp}</p>
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
