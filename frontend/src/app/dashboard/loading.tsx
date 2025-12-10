import { Skeleton } from "@/components/ui/skeleton";

export default function DashboardLoading() {
    return (
        <div className="space-y-8 p-8 max-w-7xl mx-auto pt-24">
            {/* Header Skeleton */}
            <div className="flex flex-col md:flex-row gap-4 md:items-center justify-between">
                <div>
                    <Skeleton className="h-10 w-64 mb-2" />
                    <Skeleton className="h-5 w-96" />
                </div>
                <Skeleton className="h-10 w-32" />
            </div>

            {/* Stats Cards Skeleton */}
            <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-4">
                {Array.from({ length: 4 }).map((_, i) => (
                    <Skeleton key={i} className="h-32 rounded-xl" />
                ))}
            </div>

            <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-7">
                {/* Recent Activity Skeleton */}
                <div className="col-span-4 space-y-4">
                    <Skeleton className="h-[400px] rounded-xl" />
                </div>

                {/* Team Members / Productivity Skeleton */}
                <div className="col-span-3 space-y-6">
                    <Skeleton className="h-[400px] rounded-xl" />
                </div>
            </div>
        </div>
    );
}
