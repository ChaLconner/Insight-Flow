import { DashboardLayout } from "@/components/layout/DashboardLayout";
import { ProjectsPageSkeletonContent } from "@/components/projects/ProjectsPageSkeleton";

export default function ProjectsLoading() {
  return (
    <DashboardLayout>
      <ProjectsPageSkeletonContent />
    </DashboardLayout>
  );
}
