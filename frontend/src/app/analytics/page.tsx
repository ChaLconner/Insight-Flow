"use client";

import { useState, useEffect, useRef, useCallback } from "react";

import { ProtectedLayout } from "@/components/layout/ProtectedLayout";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  TrendingUp,
  TrendingDown,
  BarChart3,
  Target,
  Clock,
  CheckCircle2,
  AlertTriangle,
  Activity,
  Download,
  Filter,
  ArrowUpRight,
  ArrowDownRight,
  RefreshCw,
  ArrowRight
} from "lucide-react";
import Link from "next/link";
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { Skeleton } from "@/components/ui/skeleton";
import { AnalyticsPeriod } from "@/types";
import { useAuthStore } from "@/stores/auth-store";
import { analyticsApi } from "@/lib/api-endpoints";
import { CustomSelect } from "@/components/ui/custom-select";
import { getAvatarUrl } from "@/lib/utils";

// Define types for analytics data
interface AnalyticsOverview {
  totalProjects: number;
  activeProjects: number;
  totalTasks: number;
  completedTasks: number;
  inProgressTasks: number;
  overdueTasks: number;
  teamMembers: number;
  completionRate: number;
  averageCompletionTime: number;
  teamVelocity: number;
}

interface AnalyticsTrend {
  metric: string;
  current: number;
  previous: number;
  change: number;
  trend: "up" | "down";
}

interface AnalyticsProject {
  name: string;
  tasks: number;
  completed: number;
  progress: number;
  velocity: "high" | "medium" | "low";
}

interface AnalyticsTeamMember {
  name: string;
  avatar?: string;
  tasks: number;
  completed: number;
  efficiency: number;
}

interface WeeklyBurndown {
  day: string;
  planned: number;
  actual: number;
}

interface AnalyticsData {
  overview: AnalyticsOverview;
  trends: AnalyticsTrend[];
  projects: AnalyticsProject[];
  team: AnalyticsTeamMember[];
  weeklyBurndown: WeeklyBurndown[];
}

export default function AnalyticsPage() {
  const [selectedPeriod, setSelectedPeriod] = useState<AnalyticsPeriod>(AnalyticsPeriod.MONTH);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [analyticsData, setAnalyticsData] = useState<AnalyticsData | null>(null);

  const { accessToken, isAuthenticated, isLoading } = useAuthStore();
  const [dataFetched, setDataFetched] = useState(false);

  // Refs to prevent duplicate API calls
  const isLoadingRef = useRef(false);
  const lastLoadTime = useRef<number>(0);

  const loadAnalyticsData = useCallback(async (forceRefresh = false) => {
    if (!accessToken) {
      return;
    }

    // Rate limiting: prevent calls within 2 seconds of each other
    const now = Date.now();
    if (!forceRefresh && now - lastLoadTime.current < 2000 && dataFetched) {
      console.log('Rate limiting: skipping loadAnalyticsData call');
      return;
    }

    // Prevent duplicate concurrent calls
    if (isLoadingRef.current) {
      console.log('Already loading analytics data, skipping duplicate call');
      return;
    }

    try {
      isLoadingRef.current = true;
      lastLoadTime.current = now;

      if (forceRefresh) {
        setRefreshing(true);
      } else {
        setLoading(true);
      }
      setError(null);

      // Try to fetch real analytics data from API
      const response = await analyticsApi.getAnalytics(selectedPeriod);
      setAnalyticsData(response);
      setDataFetched(true);
    } catch (err) {
      console.error('Error loading analytics data:', err);
      setError('Failed to load analytics data');
    } finally {
      isLoadingRef.current = false;
      setLoading(false);
      setRefreshing(false);
    }
  }, [accessToken, selectedPeriod, dataFetched]);

  useEffect(() => {
    // Fast path: Skip if we're still loading or already have data
    if (isLoading || dataFetched) { return; }

    if (isAuthenticated && accessToken) {
      loadAnalyticsData();
    } else if (!isAuthenticated) {
      setLoading(false);
    }
  }, [isAuthenticated, accessToken, isLoading, dataFetched, loadAnalyticsData]);

  useEffect(() => {
    if (dataFetched) {
      loadAnalyticsData(true);
    }
  }, [selectedPeriod, loadAnalyticsData]);

  const handleRefresh = () => {
    loadAnalyticsData(true);
  };



  const data = analyticsData;

  const getTrendIcon = (trend: string) => {
    return trend === "up" ? (
      <ArrowUpRight className="h-4 w-4 text-emerald-400" />
    ) : (
      <ArrowDownRight className="h-4 w-4 text-red-400" />
    );
  };

  const getTrendColor = (trend: string) => {
    return trend === "up" ? "text-emerald-400" : "text-red-400";
  };

  const getVelocityBadge = (velocity: string) => {
    const config = {
      high: { label: "High", color: "bg-emerald-500/20 text-emerald-400" },
      medium: { label: "Medium", color: "bg-amber-500/20 text-amber-400" },
      low: { label: "Low", color: "bg-red-500/20 text-red-400" }
    };

    return (
      <Badge className={config[velocity as keyof typeof config].color}>
        {config[velocity as keyof typeof config].label}
      </Badge>
    );
  };

  const getPeriodLabel = (period: AnalyticsPeriod) => {
    switch (period) {
      case AnalyticsPeriod.WEEK:
        return "from last week";
      case AnalyticsPeriod.MONTH:
        return "from last month";
      case AnalyticsPeriod.QUARTER:
        return "from last quarter";
      case AnalyticsPeriod.YEAR:
        return "from last year";
      default:
        return "from last period";
    }
  };

  if (loading) {
    return (
      <ProtectedLayout>
        <div className="space-y-8">
          {/* Header Skeleton */}
          <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
            <div className="space-y-2">
              <Skeleton className="h-8 w-48" />
              <Skeleton className="h-4 w-64" />
            </div>
            <div className="flex flex-wrap gap-3 w-full sm:w-auto">
              <Skeleton className="h-10 w-32" />
              <Skeleton className="h-10 w-24" />
              <Skeleton className="h-10 w-24" />
              <Skeleton className="h-10 w-24" />
            </div>
          </div>

          {/* Key Metrics Skeleton */}
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
            {[...Array(4)].map((_, i) => (
              <Card key={i} className="border-white/10 bg-white/5 backdrop-blur-sm">
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                  <Skeleton className="h-4 w-24" />
                  <Skeleton className="h-4 w-4" />
                </CardHeader>
                <CardContent>
                  <Skeleton className="h-8 w-16 mb-2" />
                  <Skeleton className="h-3 w-32" />
                </CardContent>
              </Card>
            ))}
          </div>

          {/* Trends Skeleton */}
          <Card className="border-white/10 bg-white/5 backdrop-blur-sm">
            <CardHeader>
              <Skeleton className="h-6 w-48" />
            </CardHeader>
            <CardContent>
              <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
                {[...Array(4)].map((_, i) => (
                  <div key={i} className="flex items-center justify-between p-4 rounded-lg bg-white/5">
                    <div className="space-y-2">
                      <Skeleton className="h-3 w-24" />
                      <Skeleton className="h-6 w-12" />
                    </div>
                    <div className="space-y-2">
                      <Skeleton className="h-4 w-12 ml-auto" />
                      <Skeleton className="h-3 w-20" />
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>

          {/* Performance Charts Skeleton */}
          <div className="grid gap-8 lg:grid-cols-2">
            {[...Array(2)].map((_, i) => (
              <Card key={i} className="border-white/10 bg-white/5 backdrop-blur-sm">
                <CardHeader>
                  <Skeleton className="h-6 w-48" />
                </CardHeader>
                <CardContent>
                  <div className="space-y-4">
                    {[...Array(4)].map((_, j) => (
                      <div key={j} className="flex items-center justify-between p-4 rounded-lg bg-white/5">
                        <div className="flex-1 space-y-2">
                          <div className="flex justify-between">
                            <Skeleton className="h-4 w-32" />
                            <Skeleton className="h-4 w-16" />
                          </div>
                          <Skeleton className="h-3 w-48" />
                          <Skeleton className="h-2 w-full rounded-full" />
                        </div>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      </ProtectedLayout>
    );
  }

  if (error || !data) {
    return (
      <ProtectedLayout>
        <div className="flex flex-col items-center justify-center h-64 space-y-4">
          <div className="text-red-400 text-center">
            <p className="text-lg font-medium">{error || 'No data available'}</p>
            <Button
              onClick={() => loadAnalyticsData(true)}
              className="mt-2 bg-indigo-600 hover:bg-indigo-500 text-white"
            >
              Retry
            </Button>
          </div>
        </div>
      </ProtectedLayout>
    );
  }

  return (
    <ProtectedLayout>
      <div className="space-y-8">
        {/* Header */}
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          <div>
            <h2 className="text-3xl font-bold tracking-tight text-white">Analytics</h2>
            <p className="mt-1 text-zinc-400">
              Insights and performance metrics for your projects and team.
            </p>
          </div>
          <div className="flex flex-wrap gap-3 w-full sm:w-auto">
            <CustomSelect
              value={selectedPeriod}
              onChange={(value) => setSelectedPeriod(value as AnalyticsPeriod)}
              options={[
                { value: AnalyticsPeriod.WEEK, label: "This Week" },
                { value: AnalyticsPeriod.MONTH, label: "This Month" },
                { value: AnalyticsPeriod.QUARTER, label: "This Quarter" },
                { value: AnalyticsPeriod.YEAR, label: "This Year" },
              ]}
              className="flex-1 sm:flex-none"
            />
            <Button
              variant="outline"
              onClick={handleRefresh}
              disabled={refreshing}
              className="flex-1 sm:flex-none glass border-white/10 text-white hover:bg-white/10"
            >
              <RefreshCw className={`h-4 w-4 mr-2 ${refreshing ? 'animate-spin' : ''}`} />
              {refreshing ? 'Refreshing...' : 'Refresh'}
            </Button>

          </div>
        </div>

        {/* Key Metrics */}
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          <Card className="border-white/10 bg-white/5 backdrop-blur-sm">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium text-zinc-400">
                Completion Rate
              </CardTitle>
              <Target className="h-4 w-4 text-emerald-400" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-white">{data.overview.completionRate}%</div>
              <div className="flex items-center gap-2 mt-1">
                <span className="flex items-center text-xs text-emerald-400">
                  <TrendingUp className="h-3 w-3 mr-1" />
                  +5.2%
                </span>
                <span className="text-xs text-zinc-500">{getPeriodLabel(selectedPeriod)}</span>
              </div>
            </CardContent>
          </Card>

          <Card className="border-white/10 bg-white/5 backdrop-blur-sm">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium text-zinc-400">
                Team Velocity
              </CardTitle>
              <Activity className="h-4 w-4 text-blue-400" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-white">{data.overview.teamVelocity}</div>
              <div className="flex items-center gap-2 mt-1">
                <span className="flex items-center text-xs text-emerald-400">
                  <TrendingUp className="h-3 w-3 mr-1" />
                  +8.1%
                </span>
                <span className="text-xs text-zinc-500">{getPeriodLabel(selectedPeriod)}</span>
              </div>
            </CardContent>
          </Card>

          <Card className="border-white/10 bg-white/5 backdrop-blur-sm">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium text-zinc-400">
                Avg. Completion Time
              </CardTitle>
              <Clock className="h-4 w-4 text-amber-400" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-white">{data.overview.averageCompletionTime}d</div>
              <div className="flex items-center gap-2 mt-1">
                <span className="flex items-center text-xs text-emerald-400">
                  <TrendingDown className="h-3 w-3 mr-1" />
                  -0.8d
                </span>
                <span className="text-xs text-zinc-500">{getPeriodLabel(selectedPeriod)}</span>
              </div>
            </CardContent>
          </Card>

          <Card className="border-white/10 bg-white/5 backdrop-blur-sm">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium text-zinc-400">
                Active Projects
              </CardTitle>
              <BarChart3 className="h-4 w-4 text-violet-400" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-white">{data.overview.activeProjects}</div>
              <div className="flex items-center gap-2 mt-1">
                <span className="flex items-center text-xs text-emerald-400">
                  <TrendingUp className="h-3 w-3 mr-1" />
                  +2
                </span>
                <span className="text-xs text-zinc-500">{getPeriodLabel(selectedPeriod)}</span>
              </div>
            </CardContent>
          </Card>
        </div>



        {/* Burndown Chart */}
        <Card className="border-white/10 bg-white/5 backdrop-blur-sm">
          <CardHeader>
            <CardTitle className="text-lg font-semibold text-white">Weekly Progress</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="h-[300px] w-full">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart
                  data={data.weeklyBurndown}
                  margin={{ top: 10, right: 10, left: 0, bottom: 0 }}
                >
                  <defs>
                    <linearGradient id="colorActual" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#6366f1" stopOpacity={0.3} />
                      <stop offset="95%" stopColor="#6366f1" stopOpacity={0} />
                    </linearGradient>
                    <linearGradient id="colorPlanned" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#71717a" stopOpacity={0.3} />
                      <stop offset="95%" stopColor="#71717a" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" vertical={false} />
                  <XAxis
                    dataKey="day"
                    stroke="#a1a1aa"
                    fontSize={12}
                    tickLine={false}
                    axisLine={false}
                  />
                  <YAxis
                    stroke="#a1a1aa"
                    fontSize={12}
                    tickLine={false}
                    axisLine={false}
                    tickFormatter={(value: number) => `${value}`}
                  />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: 'rgba(24, 24, 27, 0.8)',
                      borderColor: 'rgba(255,255,255,0.1)',
                      backdropFilter: 'blur(8px)',
                      color: '#fff'
                    }}
                    itemStyle={{ color: '#fff' }}
                  />
                  <Area
                    type="monotone"
                    dataKey="planned"
                    stroke="#71717a"
                    fillOpacity={1}
                    fill="url(#colorPlanned)"
                    name="Planned Tasks"
                    strokeWidth={2}
                  />
                  <Area
                    type="monotone"
                    dataKey="actual"
                    stroke="#6366f1"
                    fillOpacity={1}
                    fill="url(#colorActual)"
                    name="Actual Completed"
                    strokeWidth={2}
                  />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>

        {/* Trends */}
        <Card className="border-white/10 bg-white/5 backdrop-blur-sm">
          <CardHeader>
            <CardTitle className="text-lg font-semibold text-white">Performance Trends</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
              {data.trends.map((trend, index: number) => (
                <div key={index} className="flex items-center justify-between p-4 rounded-lg bg-white/5">
                  <div>
                    <p className="text-sm text-zinc-400">{trend.metric}</p>
                    <p className="text-lg font-semibold text-white">{trend.current}</p>
                  </div>
                  <div className="text-right">
                    <div className="flex items-center gap-1 mb-1">
                      {getTrendIcon(trend.trend)}
                      <span className={`text-sm ${getTrendColor(trend.trend)}`}>
                        {Math.abs(trend.change)}%
                      </span>
                    </div>
                    <p className="text-xs text-zinc-500">vs last period</p>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* Project Performance & Team Performance */}
        <div className="grid gap-8 lg:grid-cols-2">
          {/* Project Performance */}
          <Card className="border-white/10 bg-white/5 backdrop-blur-sm flex flex-col h-full">
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-lg font-semibold text-white">Project Performance</CardTitle>
              <Link href="/projects">
                <Button variant="ghost" size="sm" className="text-zinc-400 hover:text-white hover:bg-white/10 h-8 text-xs">
                  View All <ArrowRight className="ml-1 h-3 w-3" />
                </Button>
              </Link>
            </CardHeader>
            <CardContent className="flex-1 min-h-0">
              {data.projects.length > 0 ? (
                <div className="space-y-4 max-h-[400px] overflow-y-auto pr-2 custom-scrollbar">
                  {data.projects.map((project, index: number) => (
                    <div key={index} className="flex items-center justify-between p-4 rounded-lg bg-white/5 hover:bg-white/10 transition-colors">
                      <div className="flex-1">
                        <div className="flex items-center justify-between mb-2">
                          <h4 className="font-medium text-white">{project.name}</h4>
                          {getVelocityBadge(project.velocity)}
                        </div>
                        <div className="flex items-center gap-4 text-sm text-zinc-400">
                          <span>{project.completed}/{project.tasks} tasks</span>
                          <span>{project.progress}% complete</span>
                        </div>
                        <div className="h-2 w-full bg-white/10 rounded-full mt-2">
                          <div
                            className="h-full rounded-full bg-indigo-500 transition-all duration-500"
                            style={{ width: `${project.progress}%` }}
                          />
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="flex flex-col items-center justify-center h-[200px] text-zinc-500">
                  <BarChart3 className="h-12 w-12 mb-3 opacity-20" />
                  <p>No active projects found</p>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Team Performance */}
          <Card className="border-white/10 bg-white/5 backdrop-blur-sm flex flex-col h-full">
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-lg font-semibold text-white">Team Performance</CardTitle>
              <Link href="/users">
                <Button variant="ghost" size="sm" className="text-zinc-400 hover:text-white hover:bg-white/10 h-8 text-xs">
                  View All <ArrowRight className="ml-1 h-3 w-3" />
                </Button>
              </Link>
            </CardHeader>
            <CardContent className="flex-1 min-h-0">
              {data.team.length > 0 ? (
                <div className="space-y-4 max-h-[400px] overflow-y-auto pr-2 custom-scrollbar">
                  {data.team.map((member, index: number) => (
                    <div key={index} className="flex items-center justify-between p-4 rounded-lg bg-white/5 hover:bg-white/10 transition-colors">
                      <div className="flex items-center gap-3">
                        <div className="h-10 w-10 rounded-full bg-zinc-700 border border-white/10 flex items-center justify-center overflow-hidden shrink-0 relative group">
                          {member.avatar ? (
                            <img
                              src={getAvatarUrl(member.avatar)}
                              alt={member.name}
                              className="h-full w-full object-cover"
                              onError={(e) => {
                                e.currentTarget.style.display = 'none';
                                e.currentTarget.nextElementSibling?.classList.remove('hidden');
                              }}
                            />
                          ) : null}
                          <span className={`${member.avatar ? 'hidden' : ''} text-sm font-medium text-zinc-300`}>
                            {member.name && typeof member.name === 'string'
                              ? member.name.split(' ').map((n: string) => n[0]).join('')
                              : ''}
                          </span>
                        </div>
                        <div>
                          <h4 className="font-medium text-white">{member.name}</h4>
                          <p className="text-sm text-zinc-400">
                            {member.completed}/{member.tasks} tasks completed
                          </p>
                        </div>
                      </div>
                      <div className="text-right">
                        <div className="flex items-center gap-2">
                          <div className="text-lg font-semibold text-white">{member.efficiency}%</div>
                          {member.efficiency >= 85 ? (
                            <CheckCircle2 className="h-4 w-4 text-emerald-400" />
                          ) : member.efficiency >= 70 ? (
                            <Clock className="h-4 w-4 text-amber-400" />
                          ) : (
                            <AlertTriangle className="h-4 w-4 text-red-400" />
                          )}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="flex flex-col items-center justify-center h-[200px] text-zinc-500">
                  <Activity className="h-12 w-12 mb-3 opacity-20" />
                  <p>No team data available</p>
                </div>
              )}
            </CardContent>
          </Card>
        </div>




      </div>
    </ProtectedLayout >
  );
}