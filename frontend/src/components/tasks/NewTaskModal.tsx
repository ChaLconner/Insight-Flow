"use client";

import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  X,
  AlertCircle,
  Calendar,
  Flag,
  Briefcase,
  Layout,
  CheckCircle2,
  Tag,
  Timer,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { CustomSelect } from "@/components/ui/custom-select";
import { tasksApi, projectsApi } from "@/lib/api-endpoints";
import type { Project, Task } from "@/types";
import { TaskPriority, TaskType, TaskStatus } from "@/types";

interface NewTaskModalProps {
  isOpen: boolean;
  onClose: () => void;
  onTaskCreated: () => void;
  defaultProjectId?: string;
  task?: Task | null;
}

export function NewTaskModal({
  isOpen,
  onClose,
  onTaskCreated,
  defaultProjectId,
  task,
}: NewTaskModalProps) {
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [projectId, setProjectId] = useState(defaultProjectId ?? "");
  const [priority, setPriority] = useState<string>(TaskPriority.MEDIUM);
  const [status, setStatus] = useState<string>(TaskStatus.TODO);
  const [type, setType] = useState<string>(TaskType.FEATURE);
  const [dueDate, setDueDate] = useState("");
  const [tags, setTags] = useState("");
  const [estimatedHours, setEstimatedHours] = useState<string>("");
  const [actualHours, setActualHours] = useState<string>("");

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [projects, setProjects] = useState<Project[]>([]);

  useEffect(() => {
    if (isOpen) {
      if (task) {
        // Edit mode
        setTitle(task.title);
        setDescription(task.description ?? "");
        setProjectId(task.projectId);
        setPriority(task.priority || TaskPriority.MEDIUM);
        setStatus(task.status || TaskStatus.TODO);
        setType(task.type || TaskType.FEATURE);
        setDueDate(
          task.dueDate
            ? new Date(task.dueDate).toISOString().split("T")[0]
            : "",
        );
        setTags(task.tags ? task.tags.join(", ") : "");
        setEstimatedHours(
          task.estimatedHours ? task.estimatedHours.toString() : "",
        );
        setActualHours(task.actualHours ? task.actualHours.toString() : "");
      } else {
        // Create mode - reset fields
        setTitle("");
        setDescription("");
        setProjectId(defaultProjectId ?? "");
        setPriority(TaskPriority.MEDIUM);
        setStatus(TaskStatus.TODO);
        setType(TaskType.FEATURE);
        setDueDate("");
        setTags("");
        setEstimatedHours("");
        setActualHours("");
      }
      setError(null);
    }
  }, [isOpen, task, defaultProjectId]);

  useEffect(() => {
    if (isOpen && !defaultProjectId && !task) {
      // Fetch projects if not provided and not editing
      const fetchProjects = async () => {
        try {
          const response = await projectsApi.getProjects();
          setProjects(
            Array.isArray(response)
              ? response
              : // eslint-disable-next-line @typescript-eslint/no-explicit-any
                ((response as any).data ?? []),
          );
        } catch (err) {
          console.error("Failed to fetch projects", err);
        }
      };
      fetchProjects();
    }
  }, [isOpen, defaultProjectId, task]);

  // Update projectId when defaultProjectId changes
  useEffect(() => {
    if (defaultProjectId && !task) {
      setProjectId(defaultProjectId);
    }
  }, [defaultProjectId, task]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!title || !projectId) {
      setError("Title and Project are required");
      return;
    }

    setLoading(true);
    setError(null);

    try {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const taskData: any = {
        title,
        description,
        priority: priority as TaskPriority,
        status: status as TaskStatus,
        type: type as TaskType,
        dueDate: dueDate ? new Date(dueDate).toISOString() : undefined,
        tags: tags
          .split(",")
          .map((t) => t.trim())
          .filter(Boolean),
        estimatedHours: estimatedHours ? parseFloat(estimatedHours) : undefined,
        actualHours: actualHours ? parseFloat(actualHours) : undefined,
      };

      if (task) {
        // Update existing task
        await tasksApi.updateTask(task.id, taskData);
      } else {
        // Create new task
        await tasksApi.createTask(projectId, {
          ...taskData,
          projectId,
        });
      }
      onTaskCreated();
      onClose();
      // Reset form only if creating a new task
      if (!task) {
        setTitle("");
        setDescription("");
        if (!defaultProjectId) {
          setProjectId("");
        }
        setPriority(TaskPriority.MEDIUM);
        setStatus(TaskStatus.TODO);
        setType(TaskType.FEATURE);
        setDueDate("");
        setTags("");
        setEstimatedHours("");
        setActualHours("");
      }
    } catch (err) {
      console.error("Failed to save task", err);
      setError("Failed to save task. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  const projectOptions = projects.map((p) => ({ value: p.id, label: p.name }));

  const getPriorityColor = (p: string) => {
    switch (p) {
      case TaskPriority.URGENT:
        return "text-fuchsia-400";
      case TaskPriority.HIGH:
        return "text-red-400";
      case TaskPriority.MEDIUM:
        return "text-yellow-400";
      case TaskPriority.LOW:
      default:
        return "text-blue-400";
    }
  };

  const priorityOptions = Object.values(TaskPriority).map((p) => ({
    value: p,
    label: p.charAt(0).toUpperCase() + p.slice(1).replace("_", " "),
    color: getPriorityColor(p),
  }));

  const getStatusColor = (s: string) => {
    switch (s) {
      case TaskStatus.DONE:
        return "text-emerald-400";
      case TaskStatus.IN_PROGRESS:
        return "text-blue-400";
      case TaskStatus.IN_REVIEW:
        return "text-purple-400";
      case TaskStatus.CANCELLED:
        return "text-red-400";
      case TaskStatus.TODO:
      default:
        return "text-zinc-400";
    }
  };

  const statusOptions = Object.values(TaskStatus).map((s) => ({
    value: s,
    label: s.charAt(0).toUpperCase() + s.slice(1).replace("_", " "),
    color: getStatusColor(s),
  }));

  const typeOptions = Object.values(TaskType).map((t) => ({
    value: t,
    label: t.charAt(0).toUpperCase() + t.slice(1).replace("_", " "),
    color: "text-zinc-400",
  }));

  return (
    <AnimatePresence>
      {isOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 sm:p-6">
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
            className="absolute inset-0 bg-black/60 backdrop-blur-sm"
          />
          <motion.div
            initial={{ opacity: 0, scale: 0.95, y: 20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: 20 }}
            className="relative w-full max-w-lg rounded-2xl border border-white/10 bg-[#18181b]/95 backdrop-blur-xl shadow-2xl max-h-[90vh] overflow-y-auto"
          >
            {/* Header */}
            <div className="flex items-center justify-between px-6 py-4 border-b border-white/5 bg-white/5 sticky top-0 z-10 backdrop-blur-md">
              <div className="flex items-center gap-2">
                <Layout className="h-5 w-5 text-indigo-400" />
                <h2 className="text-lg font-semibold text-white">
                  {task ? "Edit Task" : "Create New Task"}
                </h2>
              </div>
              <Button
                variant="ghost"
                size="icon"
                onClick={onClose}
                className="h-8 w-8 text-zinc-400 hover:text-white rounded-full hover:bg-white/10 transition-colors cursor-pointer"
              >
                <X className="h-4 w-4" />
              </Button>
            </div>

            <div className="p-6">
              {error && (
                <motion.div
                  initial={{ opacity: 0, y: -10 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="mb-4 bg-red-500/10 border border-red-500/20 rounded-lg p-3 flex items-center gap-2 text-red-400 text-sm"
                >
                  <AlertCircle className="h-4 w-4" />
                  {error}
                </motion.div>
              )}

              <form onSubmit={handleSubmit} className="space-y-6">
                {/* Main Fields */}
                <div className="space-y-4">
                  <div className="space-y-1.5">
                    <label className="text-xs font-medium text-zinc-400 ml-1 uppercase tracking-wider">
                      Title
                    </label>
                    <Input
                      value={title}
                      onChange={(e) => setTitle(e.target.value)}
                      placeholder="What needs to be done?"
                      className="bg-black/20 border-white/10 text-white placeholder:text-zinc-600 focus-visible:ring-indigo-500/50 text-lg py-6"
                      autoFocus={!task}
                    />
                  </div>

                  <div className="space-y-1.5">
                    <label className="text-xs font-medium text-zinc-400 ml-1 uppercase tracking-wider">
                      Description
                    </label>
                    <Textarea
                      value={description}
                      onChange={(e) => setDescription(e.target.value)}
                      placeholder="Add details, context, and acceptance criteria..."
                      className="min-h-[120px] bg-black/20 border-white/10 text-white placeholder:text-zinc-600 focus-visible:ring-indigo-500/50 resize-none"
                    />
                  </div>
                </div>

                {/* Meta Fields Grid */}
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 pt-2">
                  {!defaultProjectId && !task && (
                    <div className="space-y-1.5 col-span-2">
                      <div className="flex items-center gap-2 text-xs font-medium text-zinc-400 ml-1 uppercase tracking-wider">
                        <Briefcase className="h-3 w-3" />
                        Project
                      </div>
                      <CustomSelect
                        value={projectId}
                        onChange={setProjectId}
                        options={projectOptions}
                        className="w-full"
                      />
                    </div>
                  )}

                  <div className="space-y-1.5">
                    <div className="flex items-center gap-2 text-xs font-medium text-zinc-400 ml-1 uppercase tracking-wider">
                      <Flag className="h-3 w-3" />
                      Priority
                    </div>
                    <CustomSelect
                      value={priority}
                      onChange={setPriority}
                      options={priorityOptions}
                      className="w-full"
                    />
                  </div>

                  <div className="space-y-1.5">
                    <div className="flex items-center gap-2 text-xs font-medium text-zinc-400 ml-1 uppercase tracking-wider">
                      <CheckCircle2 className="h-3 w-3" />
                      Status
                    </div>
                    <CustomSelect
                      value={status}
                      onChange={setStatus}
                      options={statusOptions}
                      className="w-full"
                    />
                  </div>

                  <div className="space-y-1.5">
                    <div className="flex items-center gap-2 text-xs font-medium text-zinc-400 ml-1 uppercase tracking-wider">
                      <Tag className="h-3 w-3" />
                      Type
                    </div>
                    <CustomSelect
                      value={type}
                      onChange={setType}
                      options={typeOptions}
                      className="w-full"
                    />
                  </div>

                  <div className="space-y-1.5">
                    <div className="flex items-center gap-2 text-xs font-medium text-zinc-400 ml-1 uppercase tracking-wider">
                      <Calendar className="h-3 w-3" />
                      Due Date
                    </div>
                    <div className="relative">
                      <Input
                        type="date"
                        value={dueDate}
                        onChange={(e) => setDueDate(e.target.value)}
                        className="w-full h-9 px-3 py-2 bg-white/10 border-white/10 rounded-lg text-sm text-white focus:ring-2 focus:ring-indigo-500/50 [&::-webkit-calendar-picker-indicator]:invert [&::-webkit-calendar-picker-indicator]:opacity-50 [&::-webkit-calendar-picker-indicator]:cursor-pointer [&::-webkit-calendar-picker-indicator]:hover:opacity-100 transition-colors"
                      />
                    </div>
                  </div>
                </div>

                {/* New Fields: Tags & Time Tracking */}
                <div className="space-y-4 pt-2 border-t border-white/5">
                  <div className="space-y-1.5">
                    <label className="flex items-center gap-2 text-xs font-medium text-zinc-400 ml-1 uppercase tracking-wider">
                      <Tag className="h-3 w-3" />
                      Tags (comma separated)
                    </label>
                    <Input
                      value={tags}
                      onChange={(e) => setTags(e.target.value)}
                      placeholder="frontend, bug, v1.0..."
                      className="bg-black/20 border-white/10 text-white placeholder:text-zinc-600 focus-visible:ring-indigo-500/50"
                    />
                  </div>

                  <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-1.5">
                      <label className="flex items-center gap-2 text-xs font-medium text-zinc-400 ml-1 uppercase tracking-wider">
                        <Timer className="h-3 w-3" />
                        Est. Hours
                      </label>
                      <Input
                        type="number"
                        min="0"
                        step="0.5"
                        value={estimatedHours}
                        onChange={(e) => setEstimatedHours(e.target.value)}
                        placeholder="0.0"
                        className="bg-black/20 border-white/10 text-white placeholder:text-zinc-600 focus-visible:ring-indigo-500/50"
                      />
                    </div>
                    <div className="space-y-1.5">
                      <label className="flex items-center gap-2 text-xs font-medium text-zinc-400 ml-1 uppercase tracking-wider">
                        <CheckCircle2 className="h-3 w-3" />
                        Act. Hours
                      </label>
                      <Input
                        type="number"
                        min="0"
                        step="0.5"
                        value={actualHours}
                        onChange={(e) => setActualHours(e.target.value)}
                        placeholder="0.0"
                        className="bg-black/20 border-white/10 text-white placeholder:text-zinc-600 focus-visible:ring-indigo-500/50"
                      />
                    </div>
                  </div>
                </div>

                {/* Actions */}
                <div className="flex items-center justify-end gap-3 pt-6 border-t border-white/5">
                  <Button
                    type="button"
                    variant="ghost"
                    onClick={onClose}
                    className="text-zinc-400 hover:text-white hover:bg-white/5"
                  >
                    Cancel
                  </Button>
                  <Button
                    type="submit"
                    disabled={loading}
                    className="bg-indigo-600 hover:bg-indigo-700 text-white shadow-lg shadow-indigo-500/20"
                  >
                    {loading
                      ? task
                        ? "Saving..."
                        : "Creating..."
                      : task
                        ? "Save Changes"
                        : "Create Task"}
                  </Button>
                </div>
              </form>
            </div>
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  );
}
