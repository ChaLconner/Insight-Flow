import { notFound } from "next/navigation";
import { DashboardLayout } from "@/components/layout/DashboardLayout";
import { serverApi } from "@/lib/api-server";
import type { Metadata } from "next";
import { TaskDetails } from "@/components/tasks/TaskDetails";

interface PageProps {
  params: Promise<{ id: string }>;
}

export async function generateMetadata({
  params,
}: PageProps): Promise<Metadata> {
  try {
    const { id } = await params;
    const task = await serverApi.getTask(id);
    return {
      title: `${task.title} | Insight Flow`,
      description: task.description,
    };
  } catch (_e) {
    return {
      title: "Task Not Found | Insight Flow",
    };
  }
}

export default async function TaskDetailsPage({ params }: PageProps) {
  try {
    const { id } = await params;
    const task = await serverApi.getTask(id);

    return (
      <DashboardLayout>
        <TaskDetails task={task} backLink="/tasks" backLabel="Back to Tasks" />
      </DashboardLayout>
    );
  } catch (_error) {
    notFound();
  }
}
