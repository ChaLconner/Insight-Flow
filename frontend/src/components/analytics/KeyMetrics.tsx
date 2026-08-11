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
      trend?.direction === "up" ? "text-emerald-500" : "text-destructive";
    const TrendIcon = trend?.direction === "up" ? TrendingUp : TrendingDown;

    return (
      <Card className="border-border bg-card backdrop-blur-sm hover:bg-accent/50 transition-colors">
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium text-muted-foreground">
            {title}
          </CardTitle>
          <Icon className={`h-4 w-4 ${iconColor}`} />
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold text-foreground">{value}</div>
          {trend && (
            <div className="flex items-center gap-2 mt-1">
              <span className={`flex items-center text-xs ${trendColor}`}>
                <TrendIcon className="h-3 w-3 mr-1" />
                {trend.direction === "up" ? "+" : ""}
                {trend.value}
                {trend.suffix ?? "%"}
              </span>
              <span className="text-xs text-muted-foreground">{periodLabel}</span>
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
        trend: getTrendData("completion rate") ?? getTrendData("tasks completed"),
      },
      {
        title: "Team Velocity",
        value: data.teamVelocity,
        icon: Activity,
        iconColor: "text-blue-400",
        trend: getTrendData("project velocity") ?? getTrendData("team velocity"),
      },
      {
        title: "Avg. Completion Time",
        value: `${data.averageCompletionTime}d`,
        icon: Clock,
        iconColor: "text-amber-400",
        // trend: Backend implementation needed
      },
      {
        title: "Active Projects",
        value: data.activeProjects,
        icon: BarChart3,
        iconColor: "text-violet-400",
        // trend: Backend implementation needed
      },
    ],
    [data, getTrendData],
  );

  return (
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
      {metrics.map((metric) => (
        <MetricCard
          key={metric.title}
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
