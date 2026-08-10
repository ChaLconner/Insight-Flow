"use client";

import { TaskList } from "@/components/tasks/TaskList";
import { ProtectedLayout } from "@/components/layout/ProtectedLayout";

export default function TasksPage() {
  return (
    <ProtectedLayout>
      <TaskList />
    </ProtectedLayout>
  );
}
