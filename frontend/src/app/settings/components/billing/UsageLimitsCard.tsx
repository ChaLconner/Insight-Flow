"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { History } from "lucide-react";
import type { PlanInfo } from "@/types";
import { useEffect, useState } from "react";

interface UsageStats {
  projects: number;
  seats: number;
}

interface UsageLimitsCardProps {
  usageStats: UsageStats;
  planConfig: PlanInfo;
}

export function UsageLimitsCard({ usageStats, planConfig }: UsageLimitsCardProps) {
  // Animation state
  const [mounted, setMounted] = useState(false);
  useEffect(() => {
    // Small delay to trigger animation after mount
    const timer = setTimeout(() => setMounted(true), 100);
    return () => clearTimeout(timer);
  }, []);

  const isUnlimitedProjects = planConfig.project_limit > 1000;
  const projectPercentage = isUnlimitedProjects 
    ? 0 
    : Math.min(100, (usageStats.projects / planConfig.project_limit) * 100);

  const isUnlimitedSeats = planConfig.member_limit > 1000;
  const seatsUsed = usageStats.seats;
  const seatsPercentage = isUnlimitedSeats 
    ? 0 
    : Math.min(100, (seatsUsed / planConfig.member_limit) * 100);

  return (
    <Card className="border-border bg-card">
      <CardHeader>
        <CardTitle className="text-lg font-semibold text-foreground flex items-center gap-2">
          <History className="h-5 w-5 text-indigo-500" />
          Usage Limits
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Projects Usage */}
        <div className="space-y-3">
          <div className="flex justify-between items-center">
            <span className="text-sm font-medium text-foreground">Projects</span>
            <span className="text-sm text-muted-foreground">
              {usageStats.projects} / {isUnlimitedProjects ? "Unlimited" : planConfig.project_limit} projects used
            </span>
          </div>
          <div className="h-2 rounded-full bg-muted overflow-hidden">
            <div 
              className={`h-full rounded-full transition-all duration-1000 ease-out ${projectPercentage > 90 ? 'bg-red-500' : 'bg-gradient-to-r from-indigo-500 to-purple-500'}`} 
              style={{ width: mounted ? `${projectPercentage}%` : '0%' }} 
            />
          </div>
        </div>

        {/* Seats Usage */}
        <div className="space-y-3">
          <div className="flex justify-between items-center">
            <span className="text-sm font-medium text-foreground">Team Members</span>
            <span className="text-sm text-muted-foreground">
              {seatsUsed} / {isUnlimitedSeats ? "Unlimited" : `${planConfig.member_limit} seats`} used
            </span>
          </div>
          <div className="h-2 rounded-full bg-muted overflow-hidden">
            <div 
              className={`h-full rounded-full transition-all duration-1000 ease-out ${seatsUsed > planConfig.member_limit ? 'bg-red-500' : 'bg-gradient-to-r from-emerald-500 to-teal-500'}`} 
              style={{ width: mounted ? `${seatsPercentage}%` : '0%' }} 
            />
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

export default UsageLimitsCard;
