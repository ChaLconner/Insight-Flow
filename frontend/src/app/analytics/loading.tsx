import { DashboardLayout } from "@/components/layout/DashboardLayout";
import { AnalyticsPageSkeleton } from "@/components/analytics/AnalyticsSkeletons";

export default function AnalyticsLoading() {
  return (
    <DashboardLayout>
      <AnalyticsPageSkeleton />
    </DashboardLayout>
  );
}
