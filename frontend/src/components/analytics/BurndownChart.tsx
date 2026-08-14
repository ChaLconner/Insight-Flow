"use client";

import React, { memo } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import { TrendingDown } from "lucide-react";
import type { BurndownDataPoint } from "@/app/analytics/types";

import type { AnalyticsPeriod } from "@/types";
import { getProgressTitle } from "@/utils/analytics-helpers";

interface BurndownChartProps {
  data: BurndownDataPoint[];
  period: AnalyticsPeriod;
}

// Memoized tooltip styles to prevent recreation on each render

const BurndownChartComponent: React.FC<BurndownChartProps> = ({
  data,
  period,
}) => {
  const title = getProgressTitle(period);

  // Empty state when no data is available
  if (!data || data.length === 0) {
    return (
      <Card className="border-border bg-card backdrop-blur-sm h-full flex flex-col">
        <CardHeader>
          <CardTitle className="text-lg font-semibold text-foreground flex items-center gap-2">
            <TrendingDown className="w-5 h-5 text-indigo-400" />
            {title}
          </CardTitle>
        </CardHeader>
        <CardContent className="flex-1 flex items-center justify-center">
          <div className="text-center">
            <TrendingDown className="w-12 h-12 mx-auto text-muted-foreground mb-3" />
            <p className="text-muted-foreground">No progress data available</p>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card
      className="border-border bg-card backdrop-blur-sm h-full flex flex-col overflow-hidden"
      role="figure"
      aria-label={`Burndown chart showing ${title}`}
    >
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle className="text-lg font-semibold text-foreground flex items-center gap-2">
          <TrendingDown className="w-5 h-5 text-indigo-400" />
          {title}
        </CardTitle>
      </CardHeader>
      <CardContent className="flex-1 min-w-0 overflow-hidden">
        <div className="h-[300px] w-full min-w-0">
          <ResponsiveContainer width="100%" height={300} minWidth={0}>
            <AreaChart
              data={data}
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
              <CartesianGrid
                strokeDasharray="3 3"
                stroke="rgba(255,255,255,0.1)"
                vertical={false}
              />
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
                  backgroundColor: "rgba(24, 24, 27, 0.8)",
                  borderColor: "rgba(255,255,255,0.1)",
                  backdropFilter: "blur(8px)",
                  color: "#fff",
                }}
                itemStyle={{ color: "#fff" }}
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
  );
};

// Export with memo for performance optimization
export const BurndownChart = memo(BurndownChartComponent);
