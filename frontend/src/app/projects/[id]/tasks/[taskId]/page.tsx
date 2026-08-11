import { notFound } from "next/navigation";
import { DashboardLayout } from "@/components/layout/DashboardLayout";
import { serverApi } from "@/lib/api-server";
import type { Metadata } from "next";
import { TaskDetails } from "@/components/tasks/TaskDetails";

interface PageProps {
  params: Promise<{ id: string; taskId: string }>;
}

export async function generateMetadata({
  params,
}: PageProps): Promise<Metadata> {
  try {
    const { taskId } = await params;
    const task = await serverApi.getTask(taskId);
    return {
      title: `${task.title} | Insight Flow`,
      description: task.description,
    };
  } catch (error) {
    console.warn("Failed to load task metadata:", error);
    return {
      title: "Task Not Found | Insight Flow",
    };
  }
}

export default async function TaskDetailsPage({ params }: Readonly<PageProps>) {
  try {
    const { id: projectId, taskId } = await params;
    const task = await serverApi.getTask(taskId);

    return (
      <DashboardLayout>
        <TaskDetails
          task={task}
          backLink={`/projects/${projectId}`}
          backLabel="Back to Project"
        />
      </DashboardLayout>
    );
  } catch (error) {
    console.warn("Failed to load task details:", error);
    notFound();
  }
}
