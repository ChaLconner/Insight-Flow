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
import { Flag } from "lucide-react";
import {
  analyticsTooltipStyle,
  analyticsTooltipTextStyle,
  formatAnalyticsTooltip,
} from "./chart-tooltip";

interface PriorityChartProps {
  data: { name: string; value: number }[];
}

const PRIORITY_COLORS: Record<string, string> = {
  urgent: "#e879f9", // Fuchsia
  high: "#ef4444", // Red
  medium: "#facc15", // Yellow
  low: "#3b82f6", // Blue
};

// Memoized styles

const renderPriorityLabel = ({ payload, percent, name }: PieLabelRenderProps) => {
  const displayName =
    (payload as { displayName?: string } | undefined)?.displayName ??
    String(name ?? "Unknown");
  const valuePercent = typeof percent === "number" ? percent : 0;

  return `${displayName} ${(valuePercent * 100).toFixed(0)}%`;
};

const PriorityChartComponent: React.FC<PriorityChartProps> = ({
  data = [],
}) => {
  // Memoize transformed data
  const formattedData = useMemo(
    () =>
      data.map((item) => ({
        ...item,
        displayName: item.name
          ? item.name.charAt(0).toUpperCase() + item.name.slice(1)
          : "Unknown",
      })),
    [data],
  );

  if (!data || data.length === 0) {
    return (
      <Card className="border-border bg-card backdrop-blur-sm h-full flex flex-col">
        <CardHeader>
          <CardTitle className="text-lg font-semibold text-foreground flex items-center gap-2">
            <Flag className="w-5 h-5 text-orange-400" />
            Task Priority Distribution
          </CardTitle>
        </CardHeader>
        <CardContent className="flex-1 flex items-center justify-center">
          <div className="text-center">
            <Flag className="w-12 h-12 mx-auto text-muted-foreground mb-3" />
            <p className="text-muted-foreground">No priority data available</p>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="border-border bg-card backdrop-blur-sm h-full flex flex-col">
      <CardHeader>
        <CardTitle className="text-lg font-semibold text-foreground flex items-center gap-2">
          <Flag className="w-5 h-5 text-orange-400" />
          Task Priority Distribution
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
                outerRadius={100}
                dataKey="value"
                nameKey="displayName"
                label={renderPriorityLabel}
                labelLine={false}
              >
                {formattedData.map((entry, index) => (
                  <Cell
                    key={`cell-${index}`}
                    fill={
                      PRIORITY_COLORS[entry.name.toLowerCase()] || "#6b7280"
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
export const PriorityChart = memo(PriorityChartComponent);
