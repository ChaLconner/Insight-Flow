import { ProtectedLayout } from "@/components/layout/ProtectedLayout";
import { ProjectsClient } from "@/components/projects/ProjectsClient";
import { serverApi } from "@/lib/api-server";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: 'Projects | Insight Flow',
  description: 'Manage your projects and tasks',
};

export const dynamic = 'force-dynamic';

export default async function ProjectsPage() {
  try {
    const projects = await serverApi.getProjects();

    return (
      <ProtectedLayout>
        <ProjectsClient initialProjects={projects} />
      </ProtectedLayout>
    );
  } catch (error) {
    console.error("Failed to fetch projects server-side:", error);
    return (
      <ProtectedLayout>
        <div className="flex flex-col items-center justify-center h-64 space-y-4">
          <div className="text-red-400 text-center">
            <p className="text-lg font-medium">Failed to load projects</p>
            <p className="text-sm text-zinc-500">Please try refreshing the page.</p>
          </div>
        </div>
      </ProtectedLayout>
    );
  }
}