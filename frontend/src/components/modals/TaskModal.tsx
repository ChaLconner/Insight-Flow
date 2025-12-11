"use client";

import { useState, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  X,
  Calendar,
  User,
  Flag,
  Clock,
  Tag,
  Paperclip,
  MessageCircle,
  Save,
  Loader2
} from "lucide-react";
import type { Task, CreateTaskRequest } from "@/types";
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
  [TaskPriority.LOW]: { label: "Low", color: "bg-zinc-500/20 text-zinc-400", icon: Flag },
  [TaskPriority.MEDIUM]: { label: "Medium", color: "bg-amber-500/20 text-amber-400", icon: Flag },
  [TaskPriority.HIGH]: { label: "High", color: "bg-orange-500/20 text-orange-400", icon: Flag },
  [TaskPriority.URGENT]: { label: "Urgent", color: "bg-fuchsia-500/20 text-fuchsia-400", icon: Flag },
};

const typeConfig = {
  [TaskType.FEATURE]: { label: "Feature" },
  [TaskType.BUG]: { label: "Bug" },
  [TaskType.IMPROVEMENT]: { label: "Improvement" },
  [TaskType.DOCUMENTATION]: { label: "Documentation" },
  [TaskType.RESEARCH]: { label: "Research" },
  [TaskType.OTHER]: { label: "Other" },
};

export function TaskModal({ isOpen, onClose, task, mode, onSubmit }: TaskModalProps) {
  const [formData, setFormData] = useState({
    title: task?.title || "",
    description: task?.description || "",
    projectId: task?.projectId || "",
    assigneeId: task?.assigneeId || "",
    priority: task?.priority || TaskPriority.MEDIUM,
    type: task?.type || TaskType.FEATURE,
    status: task?.status || TaskStatus.TODO,
    dueDate: task?.dueDate ? task.dueDate.split('T')[0] : "",
    estimatedHours: task?.estimatedHours || 0,
    tags: task?.tags?.join(', ') || "",
  });

  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errors, setErrors] = useState<Record<string, string>>({});

  const [projects, setProjects] = useState<any[]>([]);
  const [assignableUsers, setAssignableUsers] = useState<any[]>([]);
  const [isLoadingResources, setIsLoadingResources] = useState(false);

  // Fetch projects on mount
  useEffect(() => {
    const fetchProjects = async () => {
      try {
        const { projectsApi } = await import('@/lib/api-endpoints');
        const data = await projectsApi.getProjects(0, 100);
        setProjects(data);

        // If we're in edit mode and have a project ID, fetch its members
        if (task?.projectId) {
          const members: any = await projectsApi.getProjectMembers(task.projectId);
          if (Array.isArray(members)) {
            setAssignableUsers(members.map((m: any) => m.user));
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
        const { projectsApi } = await import('@/lib/api-endpoints');
        const members: any = await projectsApi.getProjectMembers(formData.projectId);
        if (Array.isArray(members)) {
          setAssignableUsers(members.map((m: any) => m.user));
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
    if (!formData.title.trim()) { newErrors.title = "Task title is required"; }
    if (!formData.projectId) { newErrors.projectId = "Project is required"; }

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
        dueDate: formData.dueDate || undefined,
        estimatedHours: formData.estimatedHours || undefined,
        tags: formData.tags.split(',').map(tag => tag.trim()).filter(Boolean),
      };

      await onSubmit(submitData);

      const successMessage = mode === "create"
        ? `Task "${formData.title}" created successfully`
        : `Task "${formData.title}" updated successfully`;

      toast.success(successMessage, {
        description: "Your changes have been saved.",
      });

      onClose();
    } catch (error) {
      console.error("Error submitting task:", error);
      toast.error(mode === "create" ? "Failed to create task" : "Failed to update task", {
        description: getErrorMessage(error)
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleInputChange = (field: string, value: any) => {
    setFormData(prev => ({ ...prev, [field]: value }));
    if (errors[field]) {
      setErrors(prev => ({ ...prev, [field]: "" }));
    }
  };

  const selectedProject = projects.find(p => p.id === formData.projectId);

  if (!isOpen) { return null; }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/50 backdrop-blur-sm"
        onClick={onClose}
      />

      {/* Modal */}
      <Card className="relative w-full max-w-3xl max-h-[90vh] overflow-y-auto border-white/10 bg-zinc-900/95 backdrop-blur-xl shadow-2xl">
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-6">
          <CardTitle className="text-xl font-semibold text-white">
            {mode === "create" ? "Create New Task" : "Edit Task"}
          </CardTitle>
          <Button
            variant="ghost"
            size="sm"
            onClick={onClose}
            className="h-8 w-8 p-0 text-zinc-400 hover:text-white"
          >
            <X className="h-4 w-4" />
          </Button>
        </CardHeader>

        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-6">
            {/* Basic Information */}
            <div className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="title" className="text-zinc-300">Task Title *</Label>
                <Input
                  id="title"
                  value={formData.title}
                  onChange={(e) => handleInputChange("title", e.target.value)}
                  placeholder="Enter task title"
                  className={`bg-white/5 border-white/10 text-white placeholder:text-zinc-400 ${errors.title ? "border-red-500" : ""
                    }`}
                  disabled={isSubmitting}
                />
                {errors.title && (
                  <p className="text-sm text-red-400">{errors.title}</p>
                )}
              </div>

              <div className="space-y-2">
                <Label htmlFor="description" className="text-zinc-300">Description</Label>
                <textarea
                  id="description"
                  rows={4}
                  value={formData.description}
                  onChange={(e) => handleInputChange("description", e.target.value)}
                  placeholder="Describe the task in detail..."
                  className="w-full rounded-lg bg-white/5 border border-white/10 px-3 py-2 text-white placeholder:text-zinc-400"
                  disabled={isSubmitting}
                />
              </div>
            </div>

            {/* Project and Status */}
            <div className="grid gap-4 md:grid-cols-2">
              <div className="space-y-2">
                <Label htmlFor="projectId" className="text-zinc-300">Project *</Label>
                <select
                  id="projectId"
                  value={formData.projectId}
                  onChange={(e) => handleInputChange("projectId", e.target.value)}
                  className={`w-full rounded-lg bg-white/5 border px-3 py-2 text-white text-sm ${errors.projectId ? "border-red-500" : "border-white/10"
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
                <Label htmlFor="status" className="text-zinc-300">Status</Label>
                <select
                  id="status"
                  value={formData.status}
                  onChange={(e) => handleInputChange("status", e.target.value as TaskStatus)}
                  className="w-full rounded-lg bg-white/5 border border-white/10 px-3 py-2 text-white text-sm"
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
                <Label className="text-zinc-300">Priority</Label>
                <div className="space-y-2">
                  {Object.entries(priorityConfig).map(([key, config]) => {
                    const IconComponent = config.icon;
                    return (
                      <label
                        key={key}
                        className="flex items-center gap-3 p-2 rounded-lg hover:bg-white/5 cursor-pointer"
                      >
                        <input
                          type="radio"
                          name="priority"
                          value={key}
                          checked={formData.priority === key}
                          onChange={(e) => handleInputChange("priority", e.target.value as TaskPriority)}
                          className="rounded border-white/10 bg-white/5 text-indigo-600 focus:ring-indigo-500"
                          disabled={isSubmitting}
                        />
                        <IconComponent className={`h-4 w-4 ${config.color.split(' ')[1]}`} />
                        <span className={`text-sm ${formData.priority === key ? config.color.split(' ')[1] : 'text-zinc-300'}`}>{config.label}</span>
                      </label>
                    );
                  })}
                </div>
              </div>

              <div className="space-y-2">
                <Label htmlFor="type" className="text-zinc-300">Type</Label>
                <select
                  id="type"
                  value={formData.type}
                  onChange={(e) => handleInputChange("type", e.target.value as TaskType)}
                  className="w-full rounded-lg bg-white/5 border border-white/10 px-3 py-2 text-white text-sm"
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
                <Label htmlFor="assigneeId" className="text-zinc-300">Assignee</Label>
                <select
                  id="assigneeId"
                  value={formData.assigneeId}
                  onChange={(e) => handleInputChange("assigneeId", e.target.value)}
                  className="w-full rounded-lg bg-white/5 border border-white/10 px-3 py-2 text-white text-sm"
                  disabled={isSubmitting}
                >
                  <option value="">Unassigned</option>
                  {assignableUsers.map((user) => (
                    <option key={user.id} value={user.id}>
                      {user.name || user.email || user.username}
                    </option>
                  ))}
                </select>
              </div>

              <div className="space-y-2">
                <Label htmlFor="dueDate" className="text-zinc-300">Due Date</Label>
                <div className="relative">
                  <Calendar className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-zinc-400" />
                  <Input
                    id="dueDate"
                    type="date"
                    value={formData.dueDate}
                    onChange={(e) => handleInputChange("dueDate", e.target.value)}
                    className="pl-10 bg-white/5 border-white/10 text-white"
                    disabled={isSubmitting}
                  />
                </div>
              </div>
            </div>

            {/* Estimated Hours and Tags */}
            <div className="grid gap-4 md:grid-cols-2">
              <div className="space-y-2">
                <Label htmlFor="estimatedHours" className="text-zinc-300">Estimated Hours</Label>
                <div className="relative">
                  <Clock className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-zinc-400" />
                  <Input
                    id="estimatedHours"
                    type="number"
                    min="0"
                    step="0.5"
                    value={formData.estimatedHours}
                    onChange={(e) => handleInputChange("estimatedHours", parseFloat(e.target.value) || 0)}
                    placeholder="0"
                    className="pl-10 bg-white/5 border-white/10 text-white"
                    disabled={isSubmitting}
                  />
                </div>
              </div>

              <div className="space-y-2">
                <Label htmlFor="tags" className="text-zinc-300">Tags</Label>
                <div className="relative">
                  <Tag className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-zinc-400" />
                  <Input
                    id="tags"
                    value={formData.tags}
                    onChange={(e) => handleInputChange("tags", e.target.value)}
                    placeholder="frontend, urgent, bug"
                    className="pl-10 bg-white/5 border-white/10 text-white"
                    disabled={isSubmitting}
                  />
                </div>
                <p className="text-xs text-zinc-400">Separate tags with commas</p>
              </div>
            </div>

            {/* Quick Actions */}
            <div className="flex gap-2">
              <Button
                type="button"
                variant="outline"
                size="sm"
                className="border-white/10 text-white hover:bg-white/5"
                disabled={isSubmitting}
              >
                <Paperclip className="h-4 w-4 mr-2" />
                Add Attachment
              </Button>
              <Button
                type="button"
                variant="outline"
                size="sm"
                className="border-white/10 text-white hover:bg-white/5"
                disabled={isSubmitting}
              >
                <MessageCircle className="h-4 w-4 mr-2" />
                Add Comment
              </Button>
            </div>

            {/* Actions */}
            <div className="flex gap-3 pt-6 border-t border-white/10">
              <Button
                type="button"
                variant="outline"
                onClick={onClose}
                className="flex-1 border-white/10 text-white hover:bg-white/5"
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