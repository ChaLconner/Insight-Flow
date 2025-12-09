"use client";

import { useState, useMemo } from "react";
import { ProtectedLayout } from "@/components/layout/ProtectedLayout";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Card, CardHeader, CardContent } from "@/components/ui/card";
import { AnalyticsPeriod } from "@/types";
import { useAnalytics } from "@/hooks/use-analytics";

// Components
import { AnalyticsHeader } from "@/components/analytics/AnalyticsHeader";
import { KeyMetrics } from "@/components/analytics/KeyMetrics";
import { ChartCarousel } from "@/components/analytics/ChartCarousel";
import { PerformanceTrends } from "@/components/analytics/PerformanceTrends";
import { ProjectList } from "@/components/analytics/ProjectList";
import { TeamList } from "@/components/analytics/TeamList";

export default function AnalyticsPage() {
  const [selectedPeriod, setSelectedPeriod] = useState<AnalyticsPeriod>(AnalyticsPeriod.MONTH);
  const { data, isLoading, error, refetch, isRefetching } = useAnalytics(selectedPeriod);

  const handleRefresh = () => {
    refetch();
  };

  /* Memoized data props to prevent unnecessary re-renders */
  const overviewData = useMemo(() => data?.overview, [data]);
  const burndownData = useMemo(() => data?.weeklyBurndown || [], [data]);
  const workloadData = useMemo(() => data?.teamWorkload || [], [data]);
  const dailyTrendsData = useMemo(() => data?.dailyTrends || [], [data]);
  const trendsData = useMemo(() => data?.trends || [], [data]);
  const projectsData = useMemo(() => data?.projects || [], [data]);
  const teamData = useMemo(() => data?.team || [], [data]);
  const statusDistribution = useMemo(() => data?.statusDistribution || [], [data]);
  const priorityDistribution = useMemo(() => data?.priorityDistribution || [], [data]);

  if (isLoading) {
    return (
      <ProtectedLayout>
        <div className="space-y-8">
          {/* Header Skeleton */}
          <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
            <div className="space-y-2">
              <Skeleton className="h-8 w-48" />
              <Skeleton className="h-4 w-64" />
            </div>
            <div className="flex flex-wrap gap-3 w-full sm:w-auto">
              <Skeleton className="h-10 w-32" />
              <Skeleton className="h-10 w-24" />
              <Skeleton className="h-10 w-24" />
              <Skeleton className="h-10 w-24" />
            </div>
          </div>

          {/* Key Metrics Skeleton */}
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
            {[...Array(4)].map((_, i) => (
              <Card key={i} className="border-white/10 bg-white/5 backdrop-blur-sm">
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                  <Skeleton className="h-4 w-24" />
                  <Skeleton className="h-4 w-4" />
                </CardHeader>
                <CardContent>
                  <Skeleton className="h-8 w-16 mb-2" />
                  <Skeleton className="h-3 w-32" />
                </CardContent>
              </Card>
            ))}
          </div>

          {/* Trends Skeleton */}
          <Card className="border-white/10 bg-white/5 backdrop-blur-sm">
            <CardHeader>
              <Skeleton className="h-6 w-48" />
            </CardHeader>
            <CardContent>
              <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
                {[...Array(4)].map((_, i) => (
                  <div key={i} className="flex items-center justify-between p-4 rounded-lg bg-white/5">
                    <div className="space-y-2">
                      <Skeleton className="h-3 w-24" />
                      <Skeleton className="h-6 w-12" />
                    </div>
                    <div className="space-y-2">
                      <Skeleton className="h-4 w-12 ml-auto" />
                      <Skeleton className="h-3 w-20" />
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>

          {/* Performance Charts Skeleton */}
          <div className="grid gap-8 lg:grid-cols-2">
            {[...Array(2)].map((_, i) => (
              <Card key={i} className="border-white/10 bg-white/5 backdrop-blur-sm">
                <CardHeader>
                  <Skeleton className="h-6 w-48" />
                </CardHeader>
                <CardContent>
                  <div className="space-y-4">
                    {[...Array(4)].map((_, j) => (
                      <div key={j} className="flex items-center justify-between p-4 rounded-lg bg-white/5">
                        <div className="flex-1 space-y-2">
                          <div className="flex justify-between">
                            <Skeleton className="h-4 w-32" />
                            <Skeleton className="h-4 w-16" />
                          </div>
                          <Skeleton className="h-3 w-48" />
                          <Skeleton className="h-2 w-full rounded-full" />
                        </div>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      </ProtectedLayout>
    );
  }

  if (error ?? !data) {
    return (
      <ProtectedLayout>
        <div className="flex flex-col items-center justify-center h-64 space-y-4">
          <div className="text-red-400 text-center">
            <p className="text-lg font-medium">{error instanceof Error ? error.message : 'Failed to load analytics data'}</p>
            <Button
              onClick={() => refetch()}
              className="mt-2 bg-indigo-600 hover:bg-indigo-500 text-white"
            >
              Retry
            </Button>
          </div>
        </div>
      </ProtectedLayout>
    );
  }

  return (
    <ProtectedLayout>
      <div className="space-y-8">
        <AnalyticsHeader
          onRefresh={handleRefresh}
          isRefetching={isRefetching}
        />

        {overviewData && (
          <KeyMetrics
            data={overviewData}
            period={selectedPeriod}
            trends={trendsData}
          />
        )}

        <div className="mb-12">
          <ChartCarousel
            burndownData={burndownData}
            workloadData={workloadData}
            dailyTrendsData={dailyTrendsData}
            statusDistribution={statusDistribution}
            priorityDistribution={priorityDistribution}
            period={selectedPeriod}
            setPeriod={setSelectedPeriod}
          />
        </div>

        <PerformanceTrends
          trends={trendsData}
        />

        <div className="grid gap-8 lg:grid-cols-2">
          <ProjectList
            projects={projectsData}
          />
          <TeamList
            team={teamData}
          />
        </div>
      </div>
    </ProtectedLayout >
  );
}