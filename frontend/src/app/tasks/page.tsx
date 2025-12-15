"use client";

import { useRef } from "react";
import { DashboardLayout } from "@/components/layout/DashboardLayout";
import type { TaskListRef } from "@/components/tasks/TaskList";
import { TaskList } from "@/components/tasks/TaskList";

export default function TasksPage() {
  const taskListRef = useRef<TaskListRef>(null);

  return (
    <DashboardLayout>
      <div className="space-y-8">
        {/* Header */}
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          <div>
            <h2 className="text-3xl font-bold tracking-tight text-white">
              My Tasks
            </h2>
            <p className="mt-1 text-zinc-400">
              Manage and track all your tasks across projects.
            </p>
          </div>
        </div>

        {/* Task List */}
        <TaskList
          ref={taskListRef}
          hideHeader={true}
          showProjectName={true}
          title="My Tasks"
          description="Manage and track all your tasks across projects."
        />
      </div>
    </DashboardLayout>
  );
}
