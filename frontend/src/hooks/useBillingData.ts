import { useState, useEffect } from "react";
import { apiClient } from "@/lib/api-client";
import type { PlanInfo } from "@/types";
import { toast } from "sonner";

interface UsageStats {
  projects: number;
  seats: number;
}

interface UseBillingDataReturn {
  plans: Record<string, PlanInfo>;
  usageStats: UsageStats;
  isLoading: boolean;
  error: Error | null;
  refresh: () => Promise<void>;
}

export function useBillingData(): UseBillingDataReturn {
  const [plans, setPlans] = useState<Record<string, PlanInfo>>({});
  const [usageStats, setUsageStats] = useState<UsageStats>({ projects: 0, seats: 0 });
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  const fetchData = async () => {
    setIsLoading(true);
    setError(null);
    try {
      // Parallel fetching for performance
      const [plansRes, usageRes] = await Promise.all([
        apiClient.get("/payment/plans"),
        apiClient.get("/usage/stats")
      ]);

      // Process Plans
      if (plansRes.data?.plans) {
        const plansMap: Record<string, PlanInfo> = {};
        plansRes.data.plans.forEach((p: PlanInfo) => {
          plansMap[p.plan] = p;
        });
        setPlans(plansMap);
      }

      // Process Usage
      if (usageRes.data) {
        setUsageStats({
          projects: usageRes.data.projects_used ?? 0,
          seats: usageRes.data.seats_used ?? 0
        });
      }
    } catch (err) {
      setError(err as Error);
      toast.error("Failed to load billing information", {
        description: "Please check your internet connection or try again later."
      });
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  return {
    plans,
    usageStats,
    isLoading,
    error,
    refresh: fetchData
  };
}
