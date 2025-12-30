"use client";

import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";

/**
 * UsersPageSkeleton - Loading skeleton for the users page
 * Provides visual feedback while data is loading
 */
export function UsersPageSkeleton() {
  return (
    <div className="space-y-8" role="status" aria-label="Loading users page">
      <span className="sr-only">Loading users...</span>

      {/* Header Skeleton */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div className="space-y-2">
          <Skeleton className="h-8 w-48" aria-hidden="true" />
          <Skeleton className="h-4 w-64" aria-hidden="true" />
        </div>
        <div className="flex gap-2 w-full sm:w-auto">
          <Skeleton className="h-10 w-24" aria-hidden="true" />
          <Skeleton className="h-10 w-32" aria-hidden="true" />
        </div>
      </div>

      {/* Stats Grid Skeleton */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        {[...Array(4)].map((_, i) => (
          <Card key={i} className="border-border bg-card backdrop-blur-sm">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <Skeleton className="h-4 w-24" aria-hidden="true" />
              <Skeleton className="h-4 w-4" aria-hidden="true" />
            </CardHeader>
            <CardContent>
              <Skeleton className="h-8 w-16 mb-2" aria-hidden="true" />
              <Skeleton className="h-3 w-32" aria-hidden="true" />
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Search and Filter Skeleton */}
      <div className="flex flex-col lg:flex-row gap-4">
        <Skeleton className="h-10 flex-1" aria-hidden="true" />
        <div className="flex flex-col sm:flex-row gap-2">
          <Skeleton className="h-10 w-32" aria-hidden="true" />
          <Skeleton className="h-10 w-32" aria-hidden="true" />
          <Skeleton className="h-10 w-20" aria-hidden="true" />
        </div>
      </div>

      {/* Users List Skeleton */}
      <Card className="border-border bg-card backdrop-blur-sm">
        <CardContent className="p-0">
          <div className="divide-y divide-border">
            {[...Array(5)].map((_, i) => (
              <div key={i} className="p-6">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-4">
                    <Skeleton
                      className="h-12 w-12 rounded-full"
                      aria-hidden="true"
                    />
                    <div className="space-y-2">
                      <div className="flex items-center gap-3">
                        <Skeleton className="h-5 w-32" aria-hidden="true" />
                        <Skeleton
                          className="h-5 w-20 rounded-full"
                          aria-hidden="true"
                        />
                        <Skeleton
                          className="h-5 w-20 rounded-full"
                          aria-hidden="true"
                        />
                      </div>
                      <div className="flex items-center gap-4">
                        <Skeleton className="h-4 w-48" aria-hidden="true" />
                        <Skeleton className="h-4 w-32" aria-hidden="true" />
                        <Skeleton className="h-4 w-32" aria-hidden="true" />
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <Skeleton className="h-8 w-16" aria-hidden="true" />
                    <Skeleton className="h-8 w-24" aria-hidden="true" />
                    <Skeleton className="h-8 w-8" aria-hidden="true" />
                  </div>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
