"use client";

import React, { memo } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from 'recharts';

interface WorkloadChartProps {
    data: { name: string; avatar?: string; tasks: number }[];
}

// Memoized styles
const TOOLTIP_CURSOR_STYLE = { fill: 'rgba(255,255,255,0.05)' } as const;
const TOOLTIP_CONTENT_STYLE = {
    backgroundColor: 'rgba(24, 24, 27, 0.8)',
    borderColor: 'rgba(255,255,255,0.1)',
    color: '#fff',
    borderRadius: '8px'
} as const;
const TOOLTIP_ITEM_STYLE = { color: '#fff' } as const;

const WorkloadChartComponent: React.FC<WorkloadChartProps> = ({ data = [] }) => {
    if (!data || data.length === 0) {
        return (
            <Card className="border-white/10 bg-white/5 backdrop-blur-sm h-full flex flex-col">
                <CardHeader>
                    <CardTitle className="text-lg font-semibold text-white">
                        Team Workload
                    </CardTitle>
                </CardHeader>
                <CardContent className="flex-1 flex items-center justify-center">
                    <p className="text-zinc-500">No workload data available</p>
                </CardContent>
            </Card>
        );
    }

    return (
        <Card className="border-white/10 bg-white/5 backdrop-blur-sm h-full flex flex-col">
            <CardHeader>
                <CardTitle className="text-lg font-semibold text-white">
                    Team Workload
                </CardTitle>
            </CardHeader>
            <CardContent className="flex-1">
                <div className="h-full w-full min-h-[300px]">
                    <ResponsiveContainer width="100%" height="100%">
                        <BarChart
                            layout="vertical"
                            data={data}
                            margin={{ top: 5, right: 30, left: 40, bottom: 5 }}
                        >
                            <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="rgba(255,255,255,0.1)" />
                            <XAxis type="number" stroke="#a1a1aa" fontSize={12} tickLine={false} axisLine={false} />
                            <YAxis
                                dataKey="name"
                                type="category"
                                stroke="#a1a1aa"
                                fontSize={12}
                                tickLine={false}
                                axisLine={false}
                                width={100}
                            />
                            <Tooltip
                                cursor={{ fill: 'rgba(255,255,255,0.05)' }}
                                contentStyle={{
                                    backgroundColor: 'rgba(24, 24, 27, 0.8)',
                                    borderColor: 'rgba(255,255,255,0.1)',
                                    color: '#fff',
                                    borderRadius: '8px'
                                }}
                                itemStyle={{ color: '#fff' }}
                            />
                            <Bar dataKey="tasks" fill="#8b5cf6" radius={[0, 4, 4, 0]}>
                                {data.map((entry, index) => (
                                    <Cell key={`cell-${index}`} fill="#8b5cf6" fillOpacity={0.8} />
                                ))}
                            </Bar>
                        </BarChart>
                    </ResponsiveContainer>
                </div>
            </CardContent>
        </Card>
    );
};

// Export with memo for performance optimization
export const WorkloadChart = memo(WorkloadChartComponent);
