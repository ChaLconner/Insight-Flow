import { Skeleton } from "@/components/ui/skeleton";

export default function AnalyticsLoading() {
    return (
        <div className="space-y-8 p-8 max-w-7xl mx-auto pt-24">
            {/* Header Skeleton */}
            <div className="flex flex-col md:flex-row gap-4 md:items-center justify-between">
                <Skeleton className="h-10 w-96" />
                <Skeleton className="h-10 w-48" />
            </div>

            {/* Stats Cards Skeleton */}
            <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-4">
                {Array.from({ length: 4 }).map((_, i) => (
                    <Skeleton key={i} className="h-32 rounded-xl" />
                ))}
            </div>

            {/* Main Charts Area Skeleton */}
            <div className="space-y-6">
                <Skeleton className="h-[400px] w-full rounded-xl" />
            </div>

            <div className="grid gap-6 md:grid-cols-2">
                <Skeleton className="h-[350px] rounded-xl" />
                <Skeleton className="h-[350px] rounded-xl" />
            </div>
        </div>
    );
}
