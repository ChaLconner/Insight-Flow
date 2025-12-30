"use client";

import { useState, useEffect, useId } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  X,
  Calendar,
  // User,
  Flag,
  Paperclip,
  MessageCircle,
  Save,
  Loader2,
} from "lucide-react";
import type { Task, CreateTaskRequest, Project, User, ProjectMember } from "@/types";
import { toast } from "sonner";
import { getErrorMessage } from "@/lib/error-utils";
import { TaskStatus, TaskPriority, TaskType } from "@/types";

interface TaskModalProps {
  isOpen: boolean;
  onClose: () => void;
  task?: Task | null;
  mode: "create" | "edit";
  onSubmit: (data: CreateTaskRequest) => Promise<void>;
}

const priorityConfig = {
  [TaskPriority.LOW]: {
    label: "Low",
    bgColor: "bg-slate-100 dark:bg-zinc-500/20",
    textColor: "text-slate-700 dark:text-zinc-400",
    icon: Flag,
  },
  [TaskPriority.MEDIUM]: {
    label: "Medium",
    bgColor: "bg-amber-100 dark:bg-amber-500/20",
    textColor: "text-amber-700 dark:text-amber-400",
    icon: Flag,
  },
  [TaskPriority.HIGH]: {
    label: "High",
    bgColor: "bg-orange-100 dark:bg-orange-500/20",
    textColor: "text-orange-700 dark:text-orange-400",
    icon: Flag,
  },
  [TaskPriority.URGENT]: {
    label: "Urgent",
    bgColor: "bg-fuchsia-100 dark:bg-fuchsia-500/20",
    textColor: "text-fuchsia-700 dark:text-fuchsia-400",
    icon: Flag,
  },
};

const typeConfig = {
  [TaskType.FEATURE]: { label: "Feature" },
  [TaskType.BUG]: { label: "Bug" },
  [TaskType.IMPROVEMENT]: { label: "Improvement" },
  [TaskType.DOCUMENTATION]: { label: "Documentation" },
  [TaskType.RESEARCH]: { label: "Research" },
  [TaskType.OTHER]: { label: "Other" },
};

export function TaskModal({
  isOpen,
  onClose,
  task,
  mode,
  onSubmit,
}: TaskModalProps) {
  const id = useId();
  const [formData, setFormData] = useState({
    title: task?.title ?? "",
    description: task?.description ?? "",
    projectId: task?.projectId ?? "",
    assigneeId: task?.assigneeId ?? "",
    priority: task?.priority ?? TaskPriority.MEDIUM,
    type: task?.type ?? TaskType.FEATURE,
    status: task?.status ?? TaskStatus.TODO,
    dueDate: task?.dueDate ? task.dueDate.split("T")[0] : "",

  });

  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errors, setErrors] = useState<Record<string, string>>({});

  const [projects, setProjects] = useState<Project[]>([]);
  const [assignableUsers, setAssignableUsers] = useState<User[]>([]);
  const [_isLoadingResources, _setIsLoadingResources] = useState(false);

  // Fetch projects on mount
  useEffect(() => {
    const fetchProjects = async () => {
      try {
        const { projectsApi } = await import("@/lib/api-endpoints");
        const data = await projectsApi.getProjects(0, 100);
        setProjects(data);

        // If we're in edit mode and have a project ID, fetch its members
        if (task?.projectId) {
          const members = (await projectsApi.getProjectMembers(
            task.projectId,
          )) as ProjectMember[];
          if (Array.isArray(members)) {
            setAssignableUsers(members.map((m) => m.user));
          }
        }
      } catch (error) {
        console.error("Failed to fetch projects:", error);
      }
    };
    fetchProjects();
  }, [task?.projectId]);

  // Fetch members when project changes
  useEffect(() => {
    const fetchMembers = async () => {
      if (!formData.projectId) {
        setAssignableUsers([]);
        return;
      }

      try {
        const { projectsApi } = await import("@/lib/api-endpoints");
        const members = (await projectsApi.getProjectMembers(
          formData.projectId,
        )) as ProjectMember[];
        if (Array.isArray(members)) {
          setAssignableUsers(members.map((m) => m.user));
        }
      } catch (error) {
        console.error("Failed to fetch project members:", error);
        setAssignableUsers([]);
      }
    };

    // Only fetch if it's different from the initial task project (already handled)
    // or if we just selected a new one
    if (formData.projectId && formData.projectId !== task?.projectId) {
      fetchMembers();
    }
  }, [formData.projectId, task?.projectId]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    setErrors({});

    // Validation
    const newErrors: Record<string, string> = {};
    if (!formData.title.trim()) {
      newErrors.title = "Task title is required";
    }
    if (!formData.projectId) {
      newErrors.projectId = "Project is required";
    }

    if (Object.keys(newErrors).length > 0) {
      setErrors(newErrors);
      setIsSubmitting(false);
      return;
    }

    try {
      const submitData: CreateTaskRequest = {
        title: formData.title,
        description: formData.description,
        projectId: formData.projectId,
        assigneeId: formData.assigneeId || undefined,
        priority: formData.priority,
        type: formData.type,
        dueDate: formData.dueDate ? formData.dueDate : undefined,

      };

      await onSubmit(submitData);

      const successMessage =
        mode === "create"
          ? `Task "${formData.title}" created successfully`
          : `Task "${formData.title}" updated successfully`;

      toast.success(successMessage, {
        description: "Your changes have been saved.",
      });

      onClose();
    } catch (error) {
      console.error("Error submitting task:", error);
      toast.error(
        mode === "create" ? "Failed to create task" : "Failed to update task",
        {
          description: getErrorMessage(error),
        },
      );
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleInputChange = (field: string, value: unknown) => {
    setFormData((prev) => ({ ...prev, [field]: value }));
    if (errors[field]) {
      setErrors((prev) => ({ ...prev, [field]: "" }));
    }
  };

  // const selectedProject = projects.find((p) => p.id === formData.projectId);

  if (!isOpen) {
    return null;
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/50 backdrop-blur-sm"
        onClick={onClose}
      />

      {/* Modal */}
      <Card className="relative w-full max-w-3xl max-h-[90vh] overflow-y-auto border-border bg-popover/95 backdrop-blur-xl shadow-2xl">
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-6">
          <CardTitle className="text-xl font-semibold text-foreground">
            {mode === "create" ? "Create New Task" : "Edit Task"}
          </CardTitle>
          <Button
            variant="ghost"
            size="sm"
            onClick={onClose}
            className="h-8 w-8 p-0 text-muted-foreground hover:text-foreground"
          >
            <X className="h-4 w-4" />
          </Button>
        </CardHeader>

        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-6">
            {/* Basic Information */}
            <div className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor={`${id}-title`} className="text-foreground">
                  Task Title *
                </Label>
                <Input
                  id={`${id}-title`}
                  name="title"
                  autoComplete="off"
                  value={formData.title}
                  onChange={(e) => handleInputChange("title", e.target.value)}
                  placeholder="Enter task title"
                  className={`bg-background border-border text-foreground placeholder:text-muted-foreground ${
                    errors.title ? "border-red-500" : ""
                  }`}
                  disabled={isSubmitting}
                />
                {errors.title && (
                  <p className="text-sm text-red-400">{errors.title}</p>
                )}
              </div>

              <div className="space-y-2">
                <Label htmlFor={`${id}-description`} className="text-foreground">
                  Description
                </Label>
                <textarea
                  id={`${id}-description`}
                  name="description"
                  autoComplete="off"
                  rows={4}
                  value={formData.description}
                  onChange={(e) =>
                    handleInputChange("description", e.target.value)
                  }
                  placeholder="Describe the task in detail..."
                  className="w-full rounded-lg bg-background border border-border px-3 py-2 text-foreground placeholder:text-muted-foreground"
                  disabled={isSubmitting}
                />
              </div>
            </div>

            {/* Project and Status */}
            <div className="grid gap-4 md:grid-cols-2">
              <div className="space-y-2">
                <Label htmlFor={`${id}-project`} className="text-foreground">
                  Project *
                </Label>
                <select
                  id={`${id}-project`}
                  name="projectId"
                  autoComplete="off"
                  value={formData.projectId}
                  onChange={(e) =>
                    handleInputChange("projectId", e.target.value)
                  }
                  className={`w-full rounded-lg bg-background border px-3 py-2 text-foreground text-sm ${
                    errors.projectId ? "border-red-500" : "border-border"
                  }`}
                  disabled={isSubmitting}
                >
                  <option value="">Select a project</option>
                  {projects.map((project) => (
                    <option key={project.id} value={project.id}>
                      {project.name}
                    </option>
                  ))}
                </select>
                {errors.projectId && (
                  <p className="text-sm text-red-400">{errors.projectId}</p>
                )}
              </div>

              <div className="space-y-2">
                <Label htmlFor={`${id}-status`} className="text-foreground">
                  Status
                </Label>
                <select
                  id={`${id}-status`}
                  name="status"
                  autoComplete="off"
                  value={formData.status}
                  onChange={(e) =>
                    handleInputChange("status", e.target.value as TaskStatus)
                  }
                  className="w-full rounded-lg bg-background border border-border px-3 py-2 text-foreground text-sm"
                  disabled={isSubmitting}
                >
                  <option value={TaskStatus.TODO}>To Do</option>
                  <option value={TaskStatus.IN_PROGRESS}>In Progress</option>
                  <option value={TaskStatus.IN_REVIEW}>In Review</option>
                  <option value={TaskStatus.DONE}>Done</option>
                  <option value={TaskStatus.CANCELLED}>Cancelled</option>
                </select>
              </div>
            </div>

            {/* Priority and Type */}
            <div className="grid gap-4 md:grid-cols-2">
              <div className="space-y-2">
                <Label className="text-foreground">Priority</Label>
                <div className="space-y-2">
                  {Object.entries(priorityConfig).map(([key, config]) => {
                    const IconComponent = config.icon;
                    return (
                      <label
                        key={key}
                        htmlFor={`${id}-priority-${key}`}
                        className="flex items-center gap-3 p-2 rounded-lg hover:bg-accent cursor-pointer"
                      >
                        <input
                          id={`${id}-priority-${key}`}
                          type="radio"
                          name="priority"
                          value={key}
                          checked={formData.priority === key}
                          onChange={(e) =>
                            handleInputChange(
                              "priority",
                              e.target.value as TaskPriority,
                            )
                          }
                          className="rounded border-border bg-card text-indigo-600 focus:ring-indigo-500"
                          disabled={isSubmitting}
                        />
                        <IconComponent
                          className={`h-4 w-4 ${config.textColor}`}
                        />
                        <span
                          className={`text-sm ${
                            formData.priority === key
                              ? config.textColor
                              : "text-foreground"
                          }`}
                        >
                          {config.label}
                        </span>
                      </label>
                    );
                  })}
                </div>
              </div>

              <div className="space-y-2">
                <Label htmlFor={`${id}-type`} className="text-foreground">
                  Type
                </Label>
                <select
                  id={`${id}-type`}
                  name="type"
                  autoComplete="off"
                  value={formData.type}
                  onChange={(e) =>
                    handleInputChange("type", e.target.value as TaskType)
                  }
                  className="w-full rounded-lg bg-background border border-border px-3 py-2 text-foreground text-sm"
                  disabled={isSubmitting}
                >
                  {Object.entries(typeConfig).map(([key, config]) => (
                    <option key={key} value={key}>
                      {config.label}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            {/* Assignee and Due Date */}
            <div className="grid gap-4 md:grid-cols-2">
              <div className="space-y-2">
                <Label htmlFor={`${id}-assignee`} className="text-foreground">
                  Assignee
                </Label>
                <select
                  id={`${id}-assignee`}
                  name="assigneeId"
                  autoComplete="off"
                  value={formData.assigneeId}
                  onChange={(e) =>
                    handleInputChange("assigneeId", e.target.value)
                  }
                  className="w-full rounded-lg bg-background border border-border px-3 py-2 text-foreground text-sm"
                  disabled={isSubmitting}
                >
                  <option value="">Unassigned</option>
                  {assignableUsers.map((user) => (
                    <option key={user.id} value={user.id}>
                      {user.name ?? user.email ?? user.username}
                    </option>
                  ))}
                </select>
              </div>

              <div className="space-y-2">
                <Label htmlFor={`${id}-due-date`} className="text-foreground">
                  Due Date
                </Label>
                <div className="relative">
                  <Calendar className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                  <Input
                    id={`${id}-due-date`}
                    name="dueDate"
                    autoComplete="off"
                    type="date"
                    value={formData.dueDate}
                    onChange={(e) =>
                      handleInputChange("dueDate", e.target.value)
                    }
                    className="pl-10 bg-background border-border text-foreground"
                    disabled={isSubmitting}
                  />
                </div>
              </div>
            </div>



            {/* Quick Actions */}
            <div className="flex gap-2">
              <Button
                type="button"
                variant="outline"
                size="sm"
                className="border-border text-foreground hover:bg-accent"
                disabled={isSubmitting}
              >
                <Paperclip className="h-4 w-4 mr-2" />
                Add Attachment
              </Button>
              <Button
                type="button"
                variant="outline"
                size="sm"
                className="border-border text-foreground hover:bg-accent"
                disabled={isSubmitting}
              >
                <MessageCircle className="h-4 w-4 mr-2" />
                Add Comment
              </Button>
            </div>

            {/* Actions */}
            <div className="flex gap-3 pt-6 border-t border-border">
              <Button
                type="button"
                variant="outline"
                onClick={onClose}
                className="flex-1 border-border text-foreground hover:bg-accent"
                disabled={isSubmitting}
              >
                Cancel
              </Button>
              <Button
                type="submit"
                className="flex-1 bg-indigo-600 hover:bg-indigo-500 text-white"
                disabled={isSubmitting}
              >
                {isSubmitting ? (
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                ) : (
                  <Save className="h-4 w-4 mr-2" />
                )}
                {mode === "create" ? "Create Task" : "Update Task"}
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
