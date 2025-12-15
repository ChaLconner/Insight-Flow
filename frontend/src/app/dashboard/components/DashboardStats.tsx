"use client";

import React, { memo, useMemo } from "react";
import { Briefcase, CheckCircle2, Clock, TrendingUp } from "lucide-react";
import { StatsCard } from "./StatsCard";

// Static configuration - extracted outside component to prevent recreation on each render
const STATS_CONFIG = [
  {
    key: "totalProjects",
    changeKey: "totalProjectsChange",
    trendKey: "totalProjectsTrend",
    title: "Total Projects",
    icon: Briefcase,
    color: "text-blue-400",
    bgColor: "bg-blue-400/10",
  },
  {
    key: "inProgressTasks",
    changeKey: "inProgressTasksChange",
    trendKey: "inProgressTasksTrend",
    title: "Active Tasks",
    icon: CheckCircle2,
    color: "text-emerald-400",
    bgColor: "bg-emerald-400/10",
  },
  {
    key: "pendingReviewTasks",
    changeKey: "pendingReviewTasksChange",
    trendKey: "pendingReviewTasksTrend",
    title: "Pending Review",
    icon: Clock,
    color: "text-amber-400",
    bgColor: "bg-amber-400/10",
  },
  {
    key: "teamVelocity",
    changeKey: "teamVelocityChange",
    trendKey: "teamVelocityTrend",
    title: "Team Velocity",
    icon: TrendingUp,
    color: "text-violet-400",
    bgColor: "bg-violet-400/10",
  },
] as const;

export interface DashboardStatsData {
  totalProjects: number;
  totalProjectsChange?: string;
  totalProjectsTrend?: "up" | "down";
  inProgressTasks?: number;
  inProgressTasksChange?: string;
  inProgressTasksTrend?: "up" | "down";
  pendingReviewTasks?: number;
  pendingReviewTasksChange?: string;
  pendingReviewTasksTrend?: "up" | "down";
  teamVelocity?: number;
  teamVelocityChange?: string;
  teamVelocityTrend?: "up" | "down";
}

interface DashboardStatsProps {
  stats: DashboardStatsData;
}

const DashboardStats = memo(function DashboardStats({
  stats,
}: DashboardStatsProps) {
  // Memoize the stats cards array
  const statsCards = useMemo(() => {
    return STATS_CONFIG.map((config) => {
      const value = stats[config.key as keyof DashboardStatsData];
      const change = stats[config.changeKey as keyof DashboardStatsData] as
        | string
        | undefined;
      const trend = stats[config.trendKey as keyof DashboardStatsData] as
        | "up"
        | "down"
        | undefined;

      return {
        ...config,
        value: (value ?? 0).toString(),
        change,
        trend: trend ?? "up",
      };
    });
  }, [stats]);

  return (
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
      {statsCards.map((stat) => (
        <StatsCard
          key={stat.key}
          title={stat.title}
          value={stat.value}
          change={stat.change}
          trend={stat.trend}
          icon={stat.icon}
          color={stat.color}
          bgColor={stat.bgColor}
        />
      ))}
    </div>
  );
});

DashboardStats.displayName = "DashboardStats";

export { DashboardStats };
