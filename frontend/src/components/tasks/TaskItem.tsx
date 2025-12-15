"use client";

import { memo } from "react";
import Image from "next/image";
import { format } from "date-fns";
import {
  MoreHorizontal,
  Calendar,
  User as UserIcon,
  Edit,
  Trash2,
  Flag,
  Tag,
  FolderKanban,
} from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { getAvatarUrl } from "@/lib/utils";
import type { Task } from "@/types";
import { ErrorBoundary } from "@/components/ui/error-boundary";

interface TaskItemProps {
  task: Task;
  showProjectName: boolean;
  isOpen: boolean;
  isDeleting: boolean;
  onToggleMenu: (e: React.MouseEvent, taskId: string) => void;
  onEdit: (task: Task) => void;
  onDelete: (task: Task) => void;
  onClick: (task: Task) => void;
}

export const TaskItem = memo(
  ({
    task,
    showProjectName,
    isOpen,
    // isDeleting,
    onToggleMenu,
    onEdit,
    onDelete,
    onClick,
  }: TaskItemProps) => {
    return (
      <ErrorBoundary>
        <Card
          className={`border-white/10 bg-white/5 backdrop-blur-sm hover:bg-white/10 transition-colors cursor-pointer relative group ${isOpen ? "z-20" : "z-0"}`}
          onClick={() => onClick(task)}
        >
          <CardContent className="p-4 flex items-center justify-between gap-4">
            <div className="flex items-center gap-4 flex-1 min-w-0">
              <div
                className={`h-2 w-2 rounded-full ${
                  task.status.toLowerCase() === "done"
                    ? "bg-emerald-500"
                    : task.status.toLowerCase() === "in_progress"
                      ? "bg-blue-500"
                      : task.status.toLowerCase() === "in_review"
                        ? "bg-purple-500"
                        : task.status.toLowerCase() === "cancelled"
                          ? "bg-red-500"
                          : "bg-zinc-500"
                }`}
              />
              <div className="min-w-0 flex-1">
                <h4 className="text-white font-medium truncate">
                  {task.title}
                </h4>
                <div className="flex items-center flex-wrap gap-x-4 gap-y-2 mt-1 text-xs text-zinc-400">
                  {showProjectName && task.project && (
                    <span className="flex items-center gap-1">
                      <FolderKanban className="h-3 w-3 text-zinc-400" />
                      {task.project.name}
                    </span>
                  )}
                  {task.priority && (
                    <span
                      className={`flex items-center gap-1 ${
                        task.priority === "urgent"
                          ? "text-fuchsia-400"
                          : task.priority === "high"
                            ? "text-red-400"
                            : task.priority === "medium"
                              ? "text-yellow-400"
                              : "text-blue-400"
                      }`}
                    >
                      <Flag className="h-3 w-3" />
                      <span className="capitalize">{task.priority}</span>
                    </span>
                  )}
                  {task.type && (
                    <span className="flex items-center gap-1 text-zinc-400">
                      <Tag className="h-3 w-3" />
                      <span className="capitalize">{task.type}</span>
                    </span>
                  )}
                  {task.dueDate && (
                    <span className="flex items-center gap-1">
                      <Calendar className="h-3 w-3" />
                      {format(new Date(task.dueDate), "MMM d")}
                    </span>
                  )}
                  {task.assignee && (
                    <span className="flex items-center gap-1.5">
                      {task.assignee.avatar ? (
                        <Image
                          src={getAvatarUrl(task.assignee.avatar)}
                          alt={task.assignee.firstName ?? "Assignee"}
                          width={16}
                          height={16}
                          className="rounded-full object-cover"
                        />
                      ) : null}
                      <UserIcon
                        className={`h-3 w-3 ${task.assignee.avatar ? "hidden" : ""}`}
                      />
                      {task.assignee.firstName}
                    </span>
                  )}
                </div>
              </div>
            </div>

            <div className="flex items-center gap-3">
              <Badge className={`${getStatusColor(task.status)} capitalize`}>
                {task.status.replace("_", " ")}
              </Badge>
              <div className="relative">
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-8 w-8 p-0 text-zinc-400 hover:text-white hover:bg-white/10 task-menu-trigger"
                  onClick={(e) => onToggleMenu(e, task.id)}
                  aria-label="Task actions"
                >
                  <MoreHorizontal className="h-4 w-4" aria-hidden="true" />
                </Button>

                {isOpen && (
                  <div className="absolute right-0 top-full mt-2 w-48 rounded-md border border-white/10 bg-[#18181b] shadow-xl z-50 py-1 ring-1 ring-black ring-opacity-5 focus:outline-none task-menu-dropdown">
                    <button
                      onClick={(e) => {
                        e.preventDefault();
                        e.stopPropagation();
                        onEdit(task);
                      }}
                      className="w-full flex items-center px-4 py-2 text-sm text-zinc-300 hover:bg-white/10 hover:text-white transition-colors text-left cursor-pointer"
                    >
                      <Edit className="mr-2 h-4 w-4" />
                      Edit Task
                    </button>
                    <button
                      onClick={(e) => {
                        e.preventDefault();
                        e.stopPropagation();
                        onDelete(task);
                      }}
                      className="w-full flex items-center px-4 py-2 text-sm text-red-400 hover:bg-red-500/10 hover:text-red-300 transition-colors text-left cursor-pointer"
                    >
                      <Trash2 className="mr-2 h-4 w-4" />
                      {isDeleting ? "Deleting..." : "Delete Task"}
                    </button>
                  </div>
                )}
              </div>
            </div>
          </CardContent>
        </Card>
      </ErrorBoundary>
    );
  },
);

const getStatusColor = (status: string) => {
  switch (status.toLowerCase()) {
    case "done":
    case "completed":
      return "bg-emerald-500/20 text-emerald-400";
    case "in_progress":
      return "bg-blue-500/20 text-blue-400";
    case "in_review":
      return "bg-purple-500/20 text-purple-400";
    case "cancelled":
      return "bg-red-500/20 text-red-400";
    case "todo":
      return "bg-zinc-500/20 text-zinc-400";
    default:
      return "bg-zinc-500/20 text-zinc-400";
  }
};

TaskItem.displayName = "TaskItem";
