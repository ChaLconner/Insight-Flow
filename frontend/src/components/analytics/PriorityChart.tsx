"use client";

import React, { memo, useMemo } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  PieChart,
  Pie,
  Cell,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from "recharts";

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
      <Card className="border-white/10 bg-white/5 backdrop-blur-sm h-full flex flex-col">
        <CardHeader>
          <CardTitle className="text-lg font-semibold text-white">
            Task Priority Distribution
          </CardTitle>
        </CardHeader>
        <CardContent className="flex-1 flex items-center justify-center">
          <p className="text-zinc-500">No priority data available</p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="border-white/10 bg-white/5 backdrop-blur-sm h-full flex flex-col">
      <CardHeader>
        <CardTitle className="text-lg font-semibold text-white">
          Task Priority Distribution
        </CardTitle>
      </CardHeader>
      <CardContent className="flex-1">
        <div className="h-full w-full min-h-[300px]">
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie
                data={formattedData}
                cx="50%"
                cy="45%"
                outerRadius={100}
                dataKey="value"
                nameKey="displayName"
                label={({ displayName, percent }) =>
                  `${displayName} ${(percent * 100).toFixed(0)}%`
                }
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
                contentStyle={{
                  backgroundColor: "rgba(24, 24, 27, 0.95)",
                  borderColor: "rgba(255,255,255,0.1)",
                  color: "#fff",
                  borderRadius: "8px",
                  boxShadow:
                    "0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)",
                }}
                itemStyle={{ color: "#fff" }}
                labelStyle={{ color: "#fff" }}
                formatter={(value: number, name: string) => [value, name]}
              />
              <Legend
                wrapperStyle={{ paddingTop: "20px" }}
                formatter={(value) => (
                  <span style={{ color: "#a1a1aa" }}>{value}</span>
                )}
              />
            </PieChart>
          </ResponsiveContainer>
        </div>
      </CardContent>
    </Card>
  );
};

// Export with memo for performance optimization
export const PriorityChart = memo(PriorityChartComponent);
