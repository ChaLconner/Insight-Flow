"use client";

import React, { memo, useMemo } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from "recharts";

interface CreationCompletionChartProps {
  data: { date: string; created: number; completed: number }[];
}

// Memoized styles

const CreationCompletionChartComponent: React.FC<
  CreationCompletionChartProps
> = ({ data = [] }) => {
  // Memoize data validation check
  const hasData = useMemo(
    () =>
      data &&
      data.length > 0 &&
      data.some((d) => d.created > 0 || d.completed > 0),
    [data],
  );

  if (!hasData) {
    return (
      <Card className="border-border bg-card backdrop-blur-sm h-full flex flex-col">
        <CardHeader>
          <CardTitle className="text-lg font-semibold text-foreground">
            Creation vs Completion
          </CardTitle>
        </CardHeader>
        <CardContent className="flex-1 flex items-center justify-center">
          <p className="text-muted-foreground">No trend data available</p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="border-border bg-card backdrop-blur-sm h-full flex flex-col">
      <CardHeader>
        <CardTitle className="text-lg font-semibold text-foreground">
          Creation vs Completion
        </CardTitle>
      </CardHeader>
      <CardContent className="flex-1">
        <div className="h-full w-full min-h-[300px]">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart
              data={data}
              margin={{ top: 20, right: 10, left: 0, bottom: 5 }}
            >
              <CartesianGrid
                strokeDasharray="3 3"
                vertical={false}
                stroke="rgba(255,255,255,0.1)"
              />
              <XAxis
                dataKey="date"
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
              />
              <Tooltip
                cursor={{ fill: "rgba(255,255,255,0.05)" }}
                contentStyle={{
                  backgroundColor: "rgba(24, 24, 27, 0.8)",
                  borderColor: "rgba(255,255,255,0.1)",
                  color: "#fff",
                  borderRadius: "8px",
                }}
                itemStyle={{ color: "#fff" }}
              />
              <Legend wrapperStyle={{ paddingTop: "20px" }} />
              <Bar
                dataKey="created"
                name="Created"
                fill="#f472b6"
                radius={[4, 4, 0, 0]}
              />
              <Bar
                dataKey="completed"
                name="Completed"
                fill="#4ade80"
                radius={[4, 4, 0, 0]}
              />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </CardContent>
    </Card>
  );
};

// Export with memo for performance optimization
export const CreationCompletionChart = memo(CreationCompletionChartComponent);
