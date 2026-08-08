import { useState, useEffect, useCallback } from "react";
import { apiClient } from "@/lib/api-client";
import { registerAuthenticatedCacheClearer } from "@/lib/auth-cache";
import type { PlanInfo } from "@/types";
import { toast } from "sonner";
import { useAuthStore } from "@/stores/auth-store";

const BILLING_DATA_CACHE_TTL_MS = 30_000;

type BillingDataCache = {
  plans: Record<string, PlanInfo>;
  usageStats: UsageStats;
  timestamp: number;
};

const billingDataCache: BillingDataCache = {
  plans: {},
  usageStats: { projects: 0, seats: 0 },
  timestamp: 0,
};

let billingDataPromise: Promise<{
  plans: Record<string, PlanInfo>;
  usageStats: UsageStats;
  requestId: number;
}> | null = null;
let billingDataRequestId = 0;

function hasFreshBillingCache(): boolean {
  return billingDataCache.timestamp > 0 && Date.now() - billingDataCache.timestamp < BILLING_DATA_CACHE_TTL_MS;
}

export function clearBillingDataCache(): void {
  billingDataCache.plans = {};
  billingDataCache.usageStats = { projects: 0, seats: 0 };
  billingDataCache.timestamp = 0;
  billingDataPromise = null;
  billingDataRequestId += 1;
}

export function __clearBillingDataCacheForTests(): void {
  clearBillingDataCache();
}

registerAuthenticatedCacheClearer(clearBillingDataCache);

interface UsageStats {
  projects: number;
  seats: number;
}

interface UseBillingDataReturn {
  plans: Record<string, PlanInfo>;
  usageStats: UsageStats;
  isLoading: boolean;
  error: Error | null;
  refresh: (options?: { force?: boolean }) => Promise<void>;
}

export function useBillingData(options: { silent?: boolean } = {}): UseBillingDataReturn {
  const { silent } = options;
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated);
  const isAuthInitialized = useAuthStore((state) => state.isInitialized);
  const [plans, setPlans] = useState<Record<string, PlanInfo>>({});
  const [usageStats, setUsageStats] = useState<UsageStats>({ projects: 0, seats: 0 });
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  const requestBillingData = useCallback(async (options?: { force?: boolean }) => {
    if (!options?.force && billingDataPromise) {
      return billingDataPromise;
    }

    const requestId = billingDataRequestId + 1;
    billingDataRequestId = requestId;
    const requestPromise = Promise.allSettled([apiClient.get("/payment/plans"), apiClient.get("/usage/stats")])
      .then(([plansResult, usageResult]) => {
        const plansMap: Record<string, PlanInfo> = {};
        let nextUsageStats: UsageStats = { projects: 0, seats: 0 };

        if (plansResult.status === "fulfilled" && plansResult.value.data?.plans) {
          plansResult.value.data.plans.forEach((p: PlanInfo) => {
            plansMap[p.plan] = p;
          });
        } else if (plansResult.status === "rejected") {
          throw plansResult.reason;
        }

        if (usageResult.status === "fulfilled" && usageResult.value.data) {
          nextUsageStats = {
            projects: usageResult.value.data.projects_used ?? 0,
            seats: usageResult.value.data.seats_used ?? 0,
          };
        } else if (usageResult.status === "rejected") {
          const status = (usageResult.reason as { response?: { status?: number } })?.response?.status;
          if (status !== 401) {
            console.warn("Failed to load usage stats:", usageResult.reason);
          }
        }

        if (requestId === billingDataRequestId) {
          billingDataCache.plans = plansMap;
          billingDataCache.usageStats = nextUsageStats;
          billingDataCache.timestamp = Date.now();
        }

        return {
          plans: plansMap,
          usageStats: nextUsageStats,
          requestId,
        };
      })
      .finally(() => {
        if (billingDataPromise === requestPromise) {
          billingDataPromise = null;
        }
      });

    billingDataPromise = requestPromise;
    return requestPromise;
  }, []);

  const fetchData = useCallback(async (options?: { force?: boolean }) => {
    if (!isAuthInitialized) {
      return;
    }

    if (!isAuthenticated) {
      setPlans({});
      setUsageStats({ projects: 0, seats: 0 });
      setError(null);
      setIsLoading(false);
      return;
    }

    if (!options?.force && hasFreshBillingCache()) {
      setPlans(billingDataCache.plans);
      setUsageStats(billingDataCache.usageStats);
      setError(null);
      setIsLoading(false);
      return;
    }

    setIsLoading(true);
    setError(null);
    try {
      const data = await requestBillingData(options);
      if (data.requestId === billingDataRequestId) {
        setPlans(data.plans);
        setUsageStats(data.usageStats);
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
  }, [isAuthInitialized, isAuthenticated, requestBillingData, silent]);

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
