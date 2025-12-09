
import { useQuery } from '@tanstack/react-query';
import { AnalyticsPeriod } from "@/types";
import { analyticsApi } from "@/lib/api-endpoints";
import { AnalyticsResponse } from '@/app/analytics/types';

export function useAnalytics(period: AnalyticsPeriod) {
    return useQuery<AnalyticsResponse>({
        queryKey: ["analytics", period],
        queryFn: () => analyticsApi.getAnalytics(period),
        refetchInterval: 300000, // 5 minutes
        staleTime: 60000, // 1 minute
    });
}
