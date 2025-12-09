
import React from 'react';
import { AnalyticsPeriod } from "@/types";
import { Badge } from "@/components/ui/badge";
import { ArrowUpRight, ArrowDownRight } from "lucide-react";

export const getTrendIcon = (trend: string) => {
    return trend === "up" ? (
        <ArrowUpRight className="h-4 w-4 text-emerald-400" />
    ) : (
        <ArrowDownRight className="h-4 w-4 text-red-400" />
    );
};

export const getTrendColor = (trend: string) => {
    return trend === "up" ? "text-emerald-400" : "text-red-400";
};

export const getVelocityBadge = (velocity: string) => {
    const config = {
        high: { label: "High", color: "bg-emerald-500/20 text-emerald-400" },
        medium: { label: "Medium", color: "bg-amber-500/20 text-amber-400" },
        low: { label: "Low", color: "bg-red-500/20 text-red-400" }
    };

    return (
        <Badge className={config[velocity as keyof typeof config]?.color || config.medium.color}>
            {config[velocity as keyof typeof config]?.label || config.medium.label}
        </Badge>
    );
};

export const getPeriodLabel = (period: AnalyticsPeriod) => {
    switch (period) {
        case AnalyticsPeriod.WEEK:
            return "from last week";
        case AnalyticsPeriod.MONTH:
            return "from last month";
        case AnalyticsPeriod.QUARTER:
            return "from last quarter";
        case AnalyticsPeriod.YEAR:
            return "from last year";
        default:
            return "from last period";
    }
};
