
import React, { memo } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { AnalyticsTrend } from "@/app/analytics/types";
import { getTrendIcon, getTrendColor } from "@/utils/analytics-helpers";

interface PerformanceTrendsProps {
    trends: AnalyticsTrend[];
}

const PerformanceTrendsComponent: React.FC<PerformanceTrendsProps> = ({ trends }) => {
    return (
        <Card className="border-white/10 bg-white/5 backdrop-blur-sm">
            <CardHeader>
                <CardTitle className="text-lg font-semibold text-white">Performance Trends</CardTitle>
            </CardHeader>
            <CardContent>
                <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
                    {trends.map((trend: AnalyticsTrend, index: number) => (
                        <div key={index} className="flex items-center justify-between p-4 rounded-lg bg-white/5">
                            <div>
                                <p className="text-sm text-zinc-400">{trend.metric}</p>
                                <p className="text-lg font-semibold text-white">{trend.current}</p>
                            </div>
                            <div className="text-right">
                                <div className="flex items-center gap-1 mb-1">
                                    {getTrendIcon(trend.trend)}
                                    <span className={`text-sm ${getTrendColor(trend.trend)}`}>
                                        {Math.abs(trend.change)}%
                                    </span>
                                </div>
                                <p className="text-xs text-zinc-500">vs last period</p>
                            </div>
                        </div>
                    ))}
                </div>
            </CardContent>
        </Card>
    );
};

// Export with memo for performance optimization
export const PerformanceTrends = memo(PerformanceTrendsComponent);
