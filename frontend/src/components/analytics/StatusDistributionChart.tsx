"use client";

import React, { memo, useMemo } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  PieChart as RechartsPieChart,
  Pie,
  Cell,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from "recharts";
import type { PieLabelRenderProps } from "recharts";
import { PieChart } from "lucide-react";
import {
  analyticsTooltipStyle,
  analyticsTooltipTextStyle,
  formatAnalyticsTooltip,
} from "./chart-tooltip";

interface StatusDistributionChartProps {
  data: { name: string; value: number }[];
}

const STATUS_COLORS: Record<string, string> = {
  todo: "#f59e0b", // Amber
  in_progress: "#3b82f6", // Blue
  in_review: "#8b5cf6", // Purple
  done: "#22c55e", // Green
  cancelled: "#ef4444", // Red
};

// Memoized tooltip style

// Format status name for display
const formatStatusName = (name: string): string => {
  const nameMap: Record<string, string> = {
    todo: "To Do",
    in_progress: "In Progress",
    in_review: "In Review",
    done: "Done",
    cancelled: "Cancelled",
  };
  const key = name.toLowerCase().replace(" ", "_");
  return (
    nameMap[key] ||
    name.replace("_", " ").replace(/\b\w/g, (c) => c.toUpperCase())
  );
};

const renderStatusLabel = ({ payload, percent, name }: PieLabelRenderProps) => {
  const displayName =
    (payload as { displayName?: string } | undefined)?.displayName ??
    String(name ?? "Unknown");
  const valuePercent = typeof percent === "number" ? percent : 0;

  return `${displayName} ${(valuePercent * 100).toFixed(0)}%`;
};

const StatusDistributionChartComponent: React.FC<
  StatusDistributionChartProps
> = ({ data = [] }) => {
  // Memoize transformed data to prevent recalculation on each render
  const formattedData = useMemo(
    () =>
      data.map((item) => ({
        ...item,
        displayName: formatStatusName(item.name),
      })),
    [data],
  );

  if (!data || data.length === 0) {
    return (
      <Card className="border-border bg-card backdrop-blur-sm h-full flex flex-col">
        <CardHeader>
          <CardTitle className="text-lg font-semibold text-foreground flex items-center gap-2">
            <PieChart className="w-5 h-5 text-blue-400" />
            Task Status Distribution
          </CardTitle>
        </CardHeader>
        <CardContent className="flex-1 flex items-center justify-center">
          <div className="text-center">
            <PieChart className="w-12 h-12 mx-auto text-muted-foreground mb-3" />
            <p className="text-muted-foreground">No status data available</p>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="border-border bg-card backdrop-blur-sm h-full flex flex-col">
      <CardHeader>
        <CardTitle className="text-lg font-semibold text-foreground flex items-center gap-2">
          <PieChart className="w-5 h-5 text-blue-400" />
          Task Status Distribution
        </CardTitle>
      </CardHeader>
      <CardContent className="flex-1">
        <div className="h-full w-full min-h-[300px] min-w-0">
          <ResponsiveContainer width="100%" height="100%" minWidth={0}>
            <RechartsPieChart>
              <Pie
                data={formattedData}
                cx="50%"
                cy="45%"
                innerRadius={60}
                outerRadius={100}
                paddingAngle={2}
                dataKey="value"
                nameKey="displayName"
                label={renderStatusLabel}
                labelLine={false}
              >
                {formattedData.map((entry, index) => (
                  <Cell
                    key={`cell-${index}`}
                    fill={
                      STATUS_COLORS[
                        entry.name.toLowerCase().replace(" ", "_")
                      ] || "#6b7280"
                    }
                    strokeWidth={0}
                  />
                ))}
              </Pie>
              <Tooltip
                contentStyle={analyticsTooltipStyle}
                itemStyle={analyticsTooltipTextStyle}
                labelStyle={analyticsTooltipTextStyle}
                formatter={formatAnalyticsTooltip}
              />
              <Legend
                wrapperStyle={{ paddingTop: "20px" }}
                formatter={(value) => (
                  <span className="text-muted-foreground">{value}</span>
                )}
              />
            </RechartsPieChart>
          </ResponsiveContainer>
        </div>
      </CardContent>
    </Card>
  );
};

// Export with memo for performance optimization
export const StatusDistributionChart = memo(StatusDistributionChartComponent);
