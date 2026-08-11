
import { notFound } from "next/navigation";
import { DashboardLayout } from "@/components/layout/DashboardLayout";

import { serverApi } from "@/lib/api-server";
import { ProjectDetailsClient } from "@/components/projects/ProjectDetailsClient";
import type { Metadata } from "next";

interface PageProps {
  params: Promise<{ id: string }>;
}

export async function generateMetadata({
  params,
}: PageProps): Promise<Metadata> {
  try {
    const { id } = await params;
    const project = await serverApi.getProject(id);
    return {
      title: `${project.name} | Insight Flow`,
      description: project.description,
    };
  } catch (error) {
    console.warn("Failed to load project metadata:", error);
    return {
      title: "Project Not Found | Insight Flow",
    };
  }
}

export default async function ProjectDetailsPage({ params }: Readonly<PageProps>) {
  try {
    const { id } = await params;
    const project = await serverApi.getProject(id);

    return (
      <DashboardLayout>
        <ProjectDetailsClient project={project} />
      </DashboardLayout>
    );
  } catch (error) {
    console.error("Error fetching project details:", error);
    notFound();
  }
}
