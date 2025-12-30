"use client";

import React, { memo } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ArrowUpRight, ArrowDownRight } from "lucide-react";
import type { LucideIcon } from "lucide-react";

// Static class names extracted for better performance
const CARD_CLASSES =
  "border-border bg-card hover:bg-accent/50 transition-colors cursor-pointer";
const TITLE_CLASSES = "text-sm font-medium text-muted-foreground";
const VALUE_CLASSES = "text-2xl font-bold text-foreground";

export interface StatsCardProps {
  title: string;
  value: string | number;
  change?: string;
  trend?: "up" | "down";
  icon: LucideIcon;
  color: string;
  bgColor: string;
}

const StatsCard = memo(function StatsCard({
  title,
  value,
  change,
  trend = "up",
  icon: Icon,
  color,
  bgColor,
}: StatsCardProps) {
  return (
    <Card className={CARD_CLASSES}>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className={TITLE_CLASSES}>{title}</CardTitle>
        <div className={`rounded-lg p-2 ${bgColor}`}>
          <Icon className={`h-4 w-4 ${color}`} />
        </div>
      </CardHeader>
      <CardContent>
        <div className={VALUE_CLASSES}>{value}</div>
        <div className="flex items-center gap-2 mt-1">
          <span
            className={`flex items-center text-xs ${trend === "up" ? "text-emerald-400" : "text-red-400"}`}
          >
            {trend === "up" ? (
              <ArrowUpRight className="h-3 w-3 mr-1" />
            ) : (
              <ArrowDownRight className="h-3 w-3 mr-1" />
            )}
            {change ?? "0%"}
          </span>
          <span className="text-xs text-muted-foreground">from last month</span>
        </div>
      </CardContent>
    </Card>
  );
});

StatsCard.displayName = "StatsCard";

export { StatsCard };
