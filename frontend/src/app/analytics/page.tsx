"use client";

import { useState } from "react";
import { DashboardLayout } from "@/components/layout/DashboardLayout";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  TrendingUp,
  TrendingDown,
  BarChart3,
  PieChart,
  Calendar,
  Users,
  Target,
  Clock,
  CheckCircle2,
  AlertTriangle,
  Activity,
  Download,
  Filter,
  ArrowUpRight,
  ArrowDownRight
} from "lucide-react";
import { AnalyticsPeriod } from "@/types";

export default function AnalyticsPage() {
  const [selectedPeriod, setSelectedPeriod] = useState<AnalyticsPeriod>(AnalyticsPeriod.MONTH);

  // Mock analytics data
  const mockData = {
    overview: {
      totalProjects: 12,
      activeProjects: 8,
      totalTasks: 156,
      completedTasks: 89,
      inProgressTasks: 42,
      overdueTasks: 25,
      teamMembers: 24,
      completionRate: 78.5,
      averageCompletionTime: 3.2,
      teamVelocity: 92,
    },
    trends: [
      { metric: "Tasks Completed", current: 89, previous: 76, change: 13, trend: "up" },
      { metric: "Project Velocity", current: 92, previous: 85, change: 7, trend: "up" },
      { metric: "Team Productivity", current: 85, previous: 91, change: -6, trend: "down" },
      { metric: "Bug Rate", current: 2.1, previous: 3.2, change: -1.1, trend: "down" },
    ],
    projects: [
      { name: "Website Redesign", tasks: 24, completed: 18, progress: 75, velocity: "high" },
      { name: "Mobile App", tasks: 42, completed: 28, progress: 67, velocity: "medium" },
      { name: "Marketing Campaign", tasks: 16, completed: 12, progress: 75, velocity: "high" },
      { name: "API Integration", tasks: 28, completed: 15, progress: 54, velocity: "low" },
    ],
    team: [
      { name: "Sarah Chen", tasks: 12, completed: 10, efficiency: 83 },
      { name: "Mike Ross", tasks: 8, completed: 7, efficiency: 88 },
      { name: "Alex Morgan", tasks: 15, completed: 12, efficiency: 80 },
      { name: "John Doe", tasks: 6, completed: 5, efficiency: 83 },
    ],
    weeklyBurndown: [
      { day: "Mon", planned: 20, actual: 18 },
      { day: "Tue", planned: 18, actual: 22 },
      { day: "Wed", planned: 16, actual: 15 },
      { day: "Thu", planned: 14, actual: 19 },
      { day: "Fri", planned: 12, actual: 8 },
    ]
  };

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

  return (
    <DashboardLayout>
      <div className="space-y-8">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-3xl font-bold tracking-tight text-white">Analytics</h2>
            <p className="mt-1 text-zinc-400">
              Insights and performance metrics for your projects and team.
            </p>
          </div>
          <div className="flex gap-3">
            <select
              value={selectedPeriod}
              onChange={(e) => setSelectedPeriod(e.target.value as AnalyticsPeriod)}
              className="rounded-lg bg-white/5 border border-white/10 px-3 py-2 text-white text-sm"
            >
              <option value={AnalyticsPeriod.WEEK}>This Week</option>
              <option value={AnalyticsPeriod.MONTH}>This Month</option>
              <option value={AnalyticsPeriod.QUARTER}>This Quarter</option>
              <option value={AnalyticsPeriod.YEAR}>This Year</option>
            </select>
            <Button variant="outline" className="border-white/10 text-white hover:bg-white/5">
              <Filter className="h-4 w-4 mr-2" />
              Filter
            </Button>
            <Button className="bg-indigo-600 hover:bg-indigo-500 text-white">
              <Download className="h-4 w-4 mr-2" />
              Export
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
              <div className="text-2xl font-bold text-white">{mockData.overview.completionRate}%</div>
              <div className="flex items-center gap-2 mt-1">
                <span className="flex items-center text-xs text-emerald-400">
                  <TrendingUp className="h-3 w-3 mr-1" />
                  +5.2%
                </span>
                <span className="text-xs text-zinc-500">from last month</span>
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
              <div className="text-2xl font-bold text-white">{mockData.overview.teamVelocity}</div>
              <div className="flex items-center gap-2 mt-1">
                <span className="flex items-center text-xs text-emerald-400">
                  <TrendingUp className="h-3 w-3 mr-1" />
                  +8.1%
                </span>
                <span className="text-xs text-zinc-500">from last month</span>
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
              <div className="text-2xl font-bold text-white">{mockData.overview.averageCompletionTime}d</div>
              <div className="flex items-center gap-2 mt-1">
                <span className="flex items-center text-xs text-emerald-400">
                  <TrendingDown className="h-3 w-3 mr-1" />
                  -0.8d
                </span>
                <span className="text-xs text-zinc-500">from last month</span>
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
              <div className="text-2xl font-bold text-white">{mockData.overview.activeProjects}</div>
              <div className="flex items-center gap-2 mt-1">
                <span className="flex items-center text-xs text-emerald-400">
                  <TrendingUp className="h-3 w-3 mr-1" />
                  +2
                </span>
                <span className="text-xs text-zinc-500">from last month</span>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Trends */}
        <Card className="border-white/10 bg-white/5 backdrop-blur-sm">
          <CardHeader>
            <CardTitle className="text-lg font-semibold text-white">Performance Trends</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
              {mockData.trends.map((trend, index) => (
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
          <Card className="border-white/10 bg-white/5 backdrop-blur-sm">
            <CardHeader>
              <CardTitle className="text-lg font-semibold text-white">Project Performance</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {mockData.projects.map((project, index) => (
                  <div key={index} className="flex items-center justify-between p-4 rounded-lg bg-white/5">
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
                          className="h-full rounded-full bg-indigo-500"
                          style={{ width: `${project.progress}%` }}
                        />
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>

          {/* Team Performance */}
          <Card className="border-white/10 bg-white/5 backdrop-blur-sm">
            <CardHeader>
              <CardTitle className="text-lg font-semibold text-white">Team Performance</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {mockData.team.map((member, index) => (
                  <div key={index} className="flex items-center justify-between p-4 rounded-lg bg-white/5">
                    <div className="flex items-center gap-3">
                      <div className="h-10 w-10 rounded-full bg-zinc-700 border border-white/10 flex items-center justify-center text-sm font-medium text-zinc-300">
                        {member.name && typeof member.name === 'string'
                          ? member.name.split(' ').map(n => n[0]).join('')
                          : ''}
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
            </CardContent>
          </Card>
        </div>

        {/* Burndown Chart */}
        <Card className="border-white/10 bg-white/5 backdrop-blur-sm">
          <CardHeader>
            <CardTitle className="text-lg font-semibold text-white">Weekly Burndown</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div className="flex items-center gap-6 text-sm text-zinc-400">
                <div className="flex items-center gap-2">
                  <div className="w-3 h-3 rounded bg-indigo-500"></div>
                  <span>Actual Progress</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="w-3 h-3 rounded bg-zinc-500"></div>
                  <span>Planned Progress</span>
                </div>
              </div>
              <div className="grid gap-4">
                {mockData.weeklyBurndown.map((day, index) => (
                  <div key={index} className="flex items-center gap-4">
                    <div className="w-12 text-sm text-zinc-400">{day.day}</div>
                    <div className="flex-1">
                      <div className="flex items-center gap-2">
                        <span className="text-sm text-zinc-400 w-12">Planned</span>
                        <div className="flex-1 h-3 bg-white/10 rounded-full overflow-hidden">
                          <div
                            className="h-full bg-zinc-500"
                            style={{ width: `${(day.planned / 20) * 100}%` }}
                          />
                        </div>
                        <span className="text-sm text-zinc-400 w-8">{day.planned}</span>
                      </div>
                    </div>
                    <div className="flex-1">
                      <div className="flex items-center gap-2">
                        <span className="text-sm text-zinc-400 w-12">Actual</span>
                        <div className="flex-1 h-3 bg-white/10 rounded-full overflow-hidden">
                          <div
                            className="h-full bg-indigo-500"
                            style={{ width: `${(day.actual / 22) * 100}%` }}
                          />
                        </div>
                        <span className="text-sm text-zinc-400 w-8">{day.actual}</span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Task Status Distribution */}
        <div className="grid gap-8 lg:grid-cols-2">
          <Card className="border-white/10 bg-white/5 backdrop-blur-sm">
            <CardHeader>
              <CardTitle className="text-lg font-semibold text-white">Task Status Distribution</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className="w-4 h-4 rounded bg-emerald-500"></div>
                    <span className="text-zinc-300">Completed</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-white font-medium">{mockData.overview.completedTasks}</span>
                    <span className="text-zinc-400 text-sm">
                      ({Math.round((mockData.overview.completedTasks / mockData.overview.totalTasks) * 100)}%)
                    </span>
                  </div>
                </div>
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className="w-4 h-4 rounded bg-blue-500"></div>
                    <span className="text-zinc-300">In Progress</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-white font-medium">{mockData.overview.inProgressTasks}</span>
                    <span className="text-zinc-400 text-sm">
                      ({Math.round((mockData.overview.inProgressTasks / mockData.overview.totalTasks) * 100)}%)
                    </span>
                  </div>
                </div>
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className="w-4 h-4 rounded bg-amber-500"></div>
                    <span className="text-zinc-300">Overdue</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-white font-medium">{mockData.overview.overdueTasks}</span>
                    <span className="text-zinc-400 text-sm">
                      ({Math.round((mockData.overview.overdueTasks / mockData.overview.totalTasks) * 100)}%)
                    </span>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card className="border-white/10 bg-white/5 backdrop-blur-sm">
            <CardHeader>
              <CardTitle className="text-lg font-semibold text-white">Project Status</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className="w-4 h-4 rounded bg-emerald-500"></div>
                    <span className="text-zinc-300">Active</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-white font-medium">{mockData.overview.activeProjects}</span>
                    <span className="text-zinc-400 text-sm">
                      ({Math.round((mockData.overview.activeProjects / mockData.overview.totalProjects) * 100)}%)
                    </span>
                  </div>
                </div>
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className="w-4 h-4 rounded bg-zinc-500"></div>
                    <span className="text-zinc-300">Completed</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-white font-medium">
                      {mockData.overview.totalProjects - mockData.overview.activeProjects}
                    </span>
                    <span className="text-zinc-400 text-sm">
                      ({Math.round(((mockData.overview.totalProjects - mockData.overview.activeProjects) / mockData.overview.totalProjects) * 100)}%)
                    </span>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </DashboardLayout>
  );
}