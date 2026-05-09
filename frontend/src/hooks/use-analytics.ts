// React Query automatically handles window focus and background refetching optimizations.
import { useQuery } from "@tanstack/react-query";
import type { AnalyticsPeriod } from "@/types";
import { analyticsApi } from "@/lib/api-endpoints";
import type {
  AnalyticsResponse,
  TeamWorkloadPaginatedResponse,
  TeamWorkloadParams,
} from "@/app/analytics/types";

export function useAnalytics(
  period: AnalyticsPeriod,
  options: { enabled?: boolean } = {},
) {
  return useQuery<AnalyticsResponse>({
    queryKey: ["analytics", period],
    queryFn: () => analyticsApi.getAnalytics(period),
    enabled: options.enabled ?? true,
    refetchInterval: 300000, // 5 minutes
    staleTime: 300000, // 5 minutes (analytics data doesn't change that often)
    placeholderData: (previousData) => previousData, // Keep previous data while loading new period
  });
}

export function useTeamWorkload(
  params: TeamWorkloadParams,
  options: { enabled?: boolean } = {},
) {
  return useQuery<TeamWorkloadPaginatedResponse>({
    queryKey: ["teamWorkload", params],
    queryFn: () => analyticsApi.getTeamWorkload(params),
    enabled: options.enabled ?? true,
    staleTime: 3 * 60 * 1000, // 3 minutes — workload data doesn't change often
    placeholderData: (previousData) => previousData, // Keep previous data while loading new page
  });
}
