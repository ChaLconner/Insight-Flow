"use client";

import { formatDistanceToNow } from "date-fns";
import { ProtectedLayout } from "@/components/layout/ProtectedLayout";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { useAuthStore } from "@/stores/auth-store";
import { useDashboard } from "@/hooks/use-dashboard";
import { ErrorBoundary } from "@/components/ui/error-boundary";
import { getAvatarUrl } from "@/lib/utils";
import {
  Briefcase,
  CheckCircle2,
  Clock,
  TrendingUp,
  ArrowUpRight,
  ArrowDownRight
} from "lucide-react";
import { Skeleton } from "@/components/ui/skeleton";

export default function Home() {
  const { isLoading: authLoading } = useAuthStore();
  const { data, isLoading, error } = useDashboard();

  const loading = authLoading || (isLoading && !data);

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
          <div className="grid gap-4 grid-cols-1 sm:grid-cols-2 lg:grid-cols-4">
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
          <div className="text-red-400">Failed to load dashboard data</div>
        </div>
      </ProtectedLayout>
    );
  }

  if (!data) { return null; }

  const { stats, recentProjects, recentActivities } = data;

  return (
    <ProtectedLayout>
      <ErrorBoundary>
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
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {[
              {
                title: "Total Projects",
                value: stats.totalProjects.toString(),
                change: stats.totalProjectsChange,
                trend: stats.totalProjectsTrend,
                icon: Briefcase,
                color: "text-blue-400",
                bg: "bg-blue-400/10",
              },
              {
                title: "Active Tasks",
                value: (stats.inProgressTasks || 0).toString(),
                change: stats.inProgressTasksChange,
                trend: stats.inProgressTasksTrend,
                icon: CheckCircle2,
                color: "text-emerald-400",
                bg: "bg-emerald-400/10",
              },
              {
                title: "Pending Review",
                value: (stats.pendingReviewTasks || 0).toString(),
                change: stats.pendingReviewTasksChange,
                trend: stats.pendingReviewTasksTrend,
                icon: Clock,
                color: "text-amber-400",
                bg: "bg-amber-400/10",
              },
              {
                title: "Team Velocity",
                value: `${stats.teamVelocity || 0}`,
                change: stats.teamVelocityChange,
                trend: stats.teamVelocityTrend,
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
                      {stat.change || '0%'}
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
                    <div key={project.id || i} className="group p-3 rounded-xl hover:bg-white/5 transition-all border border-transparent hover:border-white/5">
                      <div className="flex flex-col sm:flex-row sm:items-center gap-4">
                        {/* Icon & Title */}
                        <div className="grid grid-cols-[auto_minmax(0,1fr)] gap-4 w-full sm:w-auto sm:flex-1 items-center">
                          <div className={`h-12 w-12 rounded-xl flex items-center justify-center shadow-lg transition-transform group-hover:scale-105 duration-300 shrink-0`} style={{ backgroundColor: project.color || '#6366f1' }}>
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
                              <span className="text-white font-medium">{project.progress || 0}%</span>
                            </div>
                            <div className="h-1.5 w-full rounded-full bg-white/10 overflow-hidden">
                              <div
                                className="h-full rounded-full transition-all duration-500"
                                style={{ width: `${project.progress || 0}%`, backgroundColor: project.color || '#6366f1' }}
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
                    <div key={activity.id || i} className="flex gap-4">
                      <div className="relative">
                        <div className="h-8 w-8 rounded-full bg-zinc-800 border border-white/10 flex items-center justify-center overflow-hidden shrink-0 group">
                          {activity.user && activity.user.avatar ? (
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
                          <span className={`${activity.user && activity.user.avatar ? 'hidden' : ''} text-xs font-medium text-zinc-400`}>
                            {activity.user && activity.user.name && typeof activity.user.name === 'string'
                              ? activity.user.name.split(' ').map((n: string) => n[0]).join('').toUpperCase()
                              : ''}
                          </span>
                        </div>
                        {i !== recentActivities.length - 1 && (
                          <div className="absolute left-4 top-8 h-full w-px bg-white/10" />
                        )}
                      </div>
                      <div className="space-y-1">
                        <p className="text-sm text-zinc-300">
                          <span className="font-medium text-white">{activity.user ? activity.user.name : 'Unknown User'}</span>{" "}
                          {activity.action}{" "}
                          <span className="text-indigo-400">
                            {activity.target || (typeof activity.project === 'string' ? activity.project : activity.project?.name)}
                          </span>
                        </p>
                        <p className="text-xs text-zinc-500">
                          {activity.time || activity.timestamp ? formatDistanceToNow(new Date((activity.time || activity.timestamp) as string), { addSuffix: true }) : ''}
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
      </ErrorBoundary>
    </ProtectedLayout>
  );
}