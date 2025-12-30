"use client";

import React, { useMemo, memo } from "react";
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
import type { BurndownDataPoint } from "@/app/analytics/types";

import { AnalyticsPeriod } from "@/types";

interface BurndownChartProps {
  data: BurndownDataPoint[];
  period: AnalyticsPeriod;
}

// Memoized tooltip styles to prevent recreation on each render

const BurndownChartComponent: React.FC<BurndownChartProps> = ({
  data,
  period,
}) => {
  const title = useMemo(() => {
    switch (period) {
      case AnalyticsPeriod.WEEK:
        return "Weekly Progress";
      case AnalyticsPeriod.MONTH:
        return "Monthly Progress";
      case AnalyticsPeriod.QUARTER:
        return "Quarterly Progress";
      case AnalyticsPeriod.YEAR:
        return "Yearly Progress";
      default:
        return "Progress";
    }
  }, [period]);

  return (
    <Card
      className="border-border bg-card backdrop-blur-sm h-full"
      role="figure"
      aria-label={`Burndown chart showing ${title}`}
    >
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle className="text-lg font-semibold text-foreground">
          {title}
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="h-[300px] w-full">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart
              data={data}
              margin={{ top: 10, right: 5, left: 0, bottom: 0 }}
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
