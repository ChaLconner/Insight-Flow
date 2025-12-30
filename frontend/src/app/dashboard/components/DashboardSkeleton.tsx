"use client";

import React, { memo } from "react";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";

// Pre-defined arrays to avoid recreating on each render
const STATS_SKELETON_COUNT = 4;
const PROJECTS_SKELETON_COUNT = 3;
const ACTIVITIES_SKELETON_COUNT = 4;

const DashboardSkeleton = memo(function DashboardSkeleton() {
  return (
    <div className="space-y-8">
      {/* Welcome Section Skeleton */}
      <WelcomeSectionSkeleton />

      {/* Stats Grid Skeleton */}
      <StatsGridSkeleton />

      {/* Recent Projects & Activity Skeleton */}
      <div className="grid gap-8 lg:grid-cols-7">
        <ProjectsListSkeleton />
        <ActivityFeedSkeleton />
      </div>
    </div>
  );
});

// Sub-components for better organization and potential selective rendering
const WelcomeSectionSkeleton = memo(function WelcomeSectionSkeleton() {
  return (
    <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
      <div>
        {/* Show actual text immediately for LCP optimization */}
        <h2 className="text-3xl font-bold tracking-tight text-foreground">
          Dashboard
        </h2>
        <p className="text-muted-foreground">
          Here's an overview of your projects and tasks.
        </p>
      </div>
      <div className="flex items-center gap-2 flex-wrap">
        <Skeleton className="h-7 w-28" />
        <Skeleton className="h-9 w-32" />
      </div>
    </div>
  );
});

const StatsGridSkeleton = memo(function StatsGridSkeleton() {
  return (
    <div className="grid gap-4 grid-cols-1 sm:grid-cols-2 lg:grid-cols-4">
      {Array.from({ length: STATS_SKELETON_COUNT }, (_, i) => (
        <Card
          key={`stat-skeleton-${i}`}
          className="border-border bg-card backdrop-blur-sm"
        >
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <Skeleton className="h-4 w-24" />
            <Skeleton className="h-8 w-8 rounded-lg" />
          </CardHeader>
          <CardContent>
            <Skeleton className="h-8 w-16 mb-2" />
            <Skeleton className="h-3 w-32" />
          </CardContent>
        </Card>
      ))}
    </div>
  );
});

const ProjectsListSkeleton = memo(function ProjectsListSkeleton() {
  return (
    <Card className="col-span-4 border-border bg-card backdrop-blur-sm">
      <CardHeader className="flex flex-row items-center justify-between">
        <Skeleton className="h-6 w-32" />
        <Skeleton className="h-5 w-5 rounded-full" />
      </CardHeader>
      <CardContent>
        <div className="space-y-6">
          {Array.from({ length: PROJECTS_SKELETON_COUNT }, (_, i) => (
            <div
              key={`project-skeleton-${i}`}
              className="flex items-center justify-between"
            >
              <div className="flex items-center gap-4">
                <Skeleton className="h-10 w-10 rounded-lg" />
                <div className="space-y-2">
                  <Skeleton className="h-4 w-32" />
                  <Skeleton className="h-3 w-48" />
                </div>
              </div>
              <div className="flex items-center gap-4">
                <div className="hidden sm:block space-y-2">
                  <Skeleton className="h-3 w-8 ml-auto" />
                  <Skeleton className="h-1.5 w-24 rounded-full" />
                </div>
                <Skeleton className="h-5 w-16 rounded-full" />
              </div>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
});

const ActivityFeedSkeleton = memo(function ActivityFeedSkeleton() {
  return (
    <Card className="col-span-3 border-border bg-card backdrop-blur-sm">
      <CardHeader>
        <Skeleton className="h-6 w-32" />
      </CardHeader>
      <CardContent>
        <div className="space-y-8">
          {Array.from({ length: ACTIVITIES_SKELETON_COUNT }, (_, i) => (
            <div key={`activity-skeleton-${i}`} className="flex gap-4">
              <Skeleton className="h-8 w-8 rounded-full" />
              <div className="space-y-2 flex-1">
                <Skeleton className="h-4 w-full" />
                <Skeleton className="h-3 w-24" />
              </div>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
});

DashboardSkeleton.displayName = "DashboardSkeleton";
WelcomeSectionSkeleton.displayName = "WelcomeSectionSkeleton";
StatsGridSkeleton.displayName = "StatsGridSkeleton";
ProjectsListSkeleton.displayName = "ProjectsListSkeleton";
ActivityFeedSkeleton.displayName = "ActivityFeedSkeleton";

export {
  DashboardSkeleton,
  ProjectsListSkeleton,
  ActivityFeedSkeleton,
  WelcomeSectionSkeleton,
  StatsGridSkeleton,
};
