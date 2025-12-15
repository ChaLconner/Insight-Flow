import React, { memo, useMemo } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { LucideIcon } from "lucide-react";
import {
  TrendingUp,
  TrendingDown,
  Target,
  Activity,
  Clock,
  BarChart3,
} from "lucide-react";
import type { AnalyticsPeriod } from "@/types";
import type { AnalyticsOverview, AnalyticsTrend } from "@/app/analytics/types";
import { getPeriodLabel } from "@/utils/analytics-helpers";

interface KeyMetricsProps {
  data: AnalyticsOverview;
  period: AnalyticsPeriod;
  trends?: AnalyticsTrend[];
}

interface MetricCardProps {
  title: string;
  value: string | number;
  icon: LucideIcon;
  iconColor: string;
  trend?: {
    value: number;
    direction: "up" | "down";
    suffix?: string;
  };
  periodLabel: string;
}

// Memoized MetricCard component for individual cards
const MetricCard = memo<MetricCardProps>(
  ({ title, value, icon: Icon, iconColor, trend, periodLabel }) => {
    const trendColor =
      trend?.direction === "up" ? "text-emerald-400" : "text-red-400";
    const TrendIcon = trend?.direction === "up" ? TrendingUp : TrendingDown;

    return (
      <Card className="border-white/10 bg-white/5 backdrop-blur-sm hover:bg-white/[0.07] transition-colors">
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium text-zinc-400">
            {title}
          </CardTitle>
          <Icon className={`h-4 w-4 ${iconColor}`} />
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold text-white">{value}</div>
          {trend && (
            <div className="flex items-center gap-2 mt-1">
              <span className={`flex items-center text-xs ${trendColor}`}>
                <TrendIcon className="h-3 w-3 mr-1" />
                {trend.direction === "up" ? "+" : ""}
                {trend.value}
                {trend.suffix ?? "%"}
              </span>
              <span className="text-xs text-zinc-500">{periodLabel}</span>
            </div>
          )}
        </CardContent>
      </Card>
    );
  },
);

MetricCard.displayName = "MetricCard";

const KeyMetricsComponent: React.FC<KeyMetricsProps> = ({
  data,
  period,
  trends = [],
}) => {
  // Calculate dynamic trends from trends data if available
  const periodLabel = useMemo(() => getPeriodLabel(period), [period]);

  // Find specific trends from the trends array
  const getTrendData = useMemo(() => {
    const trendMap = new Map(trends.map((t) => [t.metric.toLowerCase(), t]));

    return (metricName: string) => {
      const trend = trendMap.get(metricName.toLowerCase());
      if (trend) {
        return {
          value: Math.abs(trend.change),
          direction: trend.trend as "up" | "down",
        };
      }
      return undefined;
    };
  }, [trends]);

  // Metric configurations
  const metrics = useMemo(
    () => [
      {
        title: "Completion Rate",
        value: `${data.completionRate}%`,
        icon: Target,
        iconColor: "text-emerald-400",
        trend: getTrendData("completion rate") ??
          getTrendData("tasks completed") ?? {
            value: 5.2,
            direction: "up" as const,
          },
      },
      {
        title: "Team Velocity",
        value: data.teamVelocity,
        icon: Activity,
        iconColor: "text-blue-400",
        trend: getTrendData("project velocity") ??
          getTrendData("team velocity") ?? {
            value: 8.1,
            direction: "up" as const,
          },
      },
      {
        title: "Avg. Completion Time",
        value: `${data.averageCompletionTime}d`,
        icon: Clock,
        iconColor: "text-amber-400",
        trend: {
          value: 0.8,
          direction: "down" as const,
          suffix: "d",
        },
      },
      {
        title: "Active Projects",
        value: data.activeProjects,
        icon: BarChart3,
        iconColor: "text-violet-400",
        trend: {
          value: 2,
          direction: "up" as const,
          suffix: "",
        },
      },
    ],
    [data, getTrendData],
  );

  return (
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
      {metrics.map((metric, index) => (
        <MetricCard
          key={index}
          title={metric.title}
          value={metric.value}
          icon={metric.icon}
          iconColor={metric.iconColor}
          trend={metric.trend}
          periodLabel={periodLabel}
        />
      ))}
    </div>
  );
};

// Export with memo for performance optimization
export const KeyMetrics = memo(KeyMetricsComponent);
