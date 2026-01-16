import { useState, useEffect, useCallback } from "react";
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

export function useBillingData(options: { silent?: boolean } = {}): UseBillingDataReturn {
  const { silent } = options;
  const [plans, setPlans] = useState<Record<string, PlanInfo>>({});
  const [usageStats, setUsageStats] = useState<UsageStats>({ projects: 0, seats: 0 });
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  const fetchData = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      // Parallel fetching for performance with fault tolerance
      const [plansResult, usageResult] = await Promise.allSettled([
        apiClient.get("/payment/plans"),
        apiClient.get("/usage/stats")
      ]);

      // Process Plans (Critical)
      if (plansResult.status === "fulfilled" && plansResult.value.data?.plans) {
        const plansMap: Record<string, PlanInfo> = {};
        plansResult.value.data.plans.forEach((p: PlanInfo) => {
          plansMap[p.plan] = p;
        });
        setPlans(plansMap);
      } else if (plansResult.status === "rejected") {
        throw plansResult.reason; // Re-throw to trigger catch block for critical data
      }

      // Process Usage (Non-critical)
      if (usageResult.status === "fulfilled" && usageResult.value.data) {
        setUsageStats({
          projects: usageResult.value.data.projects_used ?? 0,
          seats: usageResult.value.data.seats_used ?? 0
        });
      } else if (usageResult.status === "rejected") {
        console.warn("Failed to load usage stats:", usageResult.reason);
        // Do not throw, allow page to render with 0 usage
      }
    } catch (err) {
      setError(err as Error);
      if (!silent) {
        toast.error("Failed to load billing information", {
          description: "Please check your internet connection or try again later."
        });
      }
    } finally {
      setIsLoading(false);
    }
  }, [silent]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  return {
    plans,
    usageStats,
    isLoading,
    error,
    refresh: fetchData
  };
}
