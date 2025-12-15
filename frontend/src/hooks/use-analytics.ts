// React Query automatically handles window focus and background refetching optimizations.
import { useQuery } from "@tanstack/react-query";
import type { AnalyticsPeriod } from "@/types";
import { analyticsApi } from "@/lib/api-endpoints";
import type {
  AnalyticsResponse,
  TeamWorkloadPaginatedResponse,
  TeamWorkloadParams,
} from "@/app/analytics/types";

export function useAnalytics(period: AnalyticsPeriod) {
  return useQuery<AnalyticsResponse>({
    queryKey: ["analytics", period],
    queryFn: () => analyticsApi.getAnalytics(period),
    refetchInterval: 300000, // 5 minutes
    staleTime: 300000, // 5 minutes (analytics data doesn't change that often)
    placeholderData: (previousData) => previousData, // Keep previous data while loading new period
  });
}

export function useTeamWorkload(params: TeamWorkloadParams) {
  return useQuery<TeamWorkloadPaginatedResponse>({
    queryKey: ["teamWorkload", params],
    queryFn: () => analyticsApi.getTeamWorkload(params),
    staleTime: 60000, // 1 minute
    placeholderData: (previousData) => previousData, // Keep previous data while loading new page
  });
}
