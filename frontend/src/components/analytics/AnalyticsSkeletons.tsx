import React, { memo } from "react";
import { Skeleton } from "@/components/ui/skeleton";
import { Card, CardHeader, CardContent } from "@/components/ui/card";
import { ProtectedLayout } from "@/components/layout/ProtectedLayout";

export const MetricCardSkeleton = memo(function MetricCardSkeleton() {
  return (
    <Card className="border-white/10 bg-white/5 backdrop-blur-sm">
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <Skeleton className="h-4 w-24" />
        <Skeleton className="h-4 w-4" />
      </CardHeader>
      <CardContent>
        <Skeleton className="h-8 w-16 mb-2" />
        <Skeleton className="h-3 w-32" />
      </CardContent>
    </Card>
  );
});

export const TrendItemSkeleton = memo(function TrendItemSkeleton() {
  return (
    <div className="flex items-center justify-between p-4 rounded-lg bg-white/5">
      <div className="space-y-2">
        <Skeleton className="h-3 w-24" />
        <Skeleton className="h-6 w-12" />
      </div>
      <div className="space-y-2">
        <Skeleton className="h-4 w-12 ml-auto" />
        <Skeleton className="h-3 w-20" />
      </div>
    </div>
  );
});

export const PerformanceCardItemSkeleton = memo(
  function PerformanceCardItemSkeleton() {
    return (
      <div className="flex items-center justify-between p-4 rounded-lg bg-white/5">
        <div className="flex-1 space-y-2">
          <div className="flex justify-between">
            <Skeleton className="h-4 w-32" />
            <Skeleton className="h-4 w-16" />
          </div>
          <Skeleton className="h-3 w-48" />
          <Skeleton className="h-2 w-full rounded-full" />
        </div>
      </div>
    );
  },
);

export const PerformanceCardSkeleton = memo(function PerformanceCardSkeleton() {
  return (
    <Card className="border-white/10 bg-white/5 backdrop-blur-sm">
      <CardHeader>
        <Skeleton className="h-6 w-48" />
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          {Array.from({ length: 4 }, (_, j) => (
            <PerformanceCardItemSkeleton key={j} />
          ))}
        </div>
      </CardContent>
    </Card>
  );
});

export const PerformanceTrendsSkeleton = memo(
  function PerformanceTrendsSkeleton() {
    return (
      <Card className="border-white/10 bg-white/5 backdrop-blur-sm">
        <CardHeader>
          <Skeleton className="h-6 w-48" />
        </CardHeader>
        <CardContent>
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
            {Array.from({ length: 4 }, (_, i) => (
              <TrendItemSkeleton key={i} />
            ))}
          </div>
        </CardContent>
      </Card>
    );
  },
);

export const ListSkeleton = memo(function ListSkeleton({
  title: _title,
}: {
  title: string;
}) {
  return (
    <Card className="border-white/10 bg-white/5 backdrop-blur-sm">
      <CardHeader>
        <Skeleton className="h-6 w-48" />
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          {Array.from({ length: 4 }, (_, j) => (
            <PerformanceCardItemSkeleton key={j} />
          ))}
        </div>
      </CardContent>
    </Card>
  );
});

export const ChartCarouselSkeleton = memo(function ChartCarouselSkeleton() {
  return (
    <div className="h-[450px] rounded-xl border border-white/5 bg-white/5 backdrop-blur-sm flex items-center justify-center">
      <div className="flex flex-col items-center gap-3">
        <div className="w-10 h-10 border-2 border-violet-500/30 border-t-violet-500 rounded-full animate-spin" />
        <Skeleton className="h-4 w-32" />
      </div>
    </div>
  );
});

export const HeaderSkeleton = memo(function HeaderSkeleton() {
  return (
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
  );
});

export const AnalyticsPageSkeleton = memo(function AnalyticsPageSkeleton() {
  return (
    <ProtectedLayout>
      <div className="space-y-8">
        <HeaderSkeleton />

        {/* Key Metrics Skeleton */}
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          {Array.from({ length: 4 }, (_, i) => (
            <MetricCardSkeleton key={i} />
          ))}
        </div>

        {/* Chart Carousel Skeleton */}
        <ChartCarouselSkeleton />

        {/* Trends Skeleton */}
        <PerformanceTrendsSkeleton />

        {/* Performance Charts Skeleton */}
        <div className="grid gap-8 lg:grid-cols-2">
          {Array.from({ length: 2 }, (_, i) => (
            <PerformanceCardSkeleton key={i} />
          ))}
        </div>
      </div>
    </ProtectedLayout>
  );
});
