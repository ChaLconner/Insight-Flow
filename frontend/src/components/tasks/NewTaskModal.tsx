"use client";

import { useMemo, useRef, useState, useEffect, useId } from "react";
import { motion } from "framer-motion";
import {
  X,
  AlertCircle,
  Calendar,
  Flag,
  Briefcase,
  Layout,
  CheckCircle2,
  Tag,
} from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { CustomSelect } from "@/components/ui/custom-select";
import { AnimatedModalShell } from "@/components/modals/AnimatedModalShell";
import { tasksApi, projectsApi } from "@/lib/api-endpoints";
import { registerAuthenticatedCacheClearer } from "@/lib/auth-cache";
import type { Project, Task, CreateTaskRequest, UpdateTaskRequest } from "@/types";
import { TaskPriority, TaskType, TaskStatus } from "@/types";

interface NewTaskModalProps {
  isOpen: boolean;
  onClose: () => void;
  onTaskCreated: () => void;
  defaultProjectId?: string;
  task?: Task | null;
}

const PROJECT_CACHE_TTL_MS = 60_000;
let projectsCacheGeneration = 0;
let projectsCache: { expiresAt: number; data: Project[] } | null = null;

export function clearNewTaskModalCache(): void {
  projectsCache = null;
  projectsCacheGeneration += 1;
}

registerAuthenticatedCacheClearer(clearNewTaskModalCache);

export function NewTaskModal({
  isOpen,
  onClose,
  onTaskCreated,
  defaultProjectId,
  task,
}: Readonly<NewTaskModalProps>) {
  const id = useId();
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [projectId, setProjectId] = useState(defaultProjectId ?? "");
  const [priority, setPriority] = useState<string>(TaskPriority.MEDIUM);
  const [status, setStatus] = useState<string>(TaskStatus.TODO);
  const [type, setType] = useState<string>(TaskType.FEATURE);
  const [dueDate, setDueDate] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [projects, setProjects] = useState<Project[]>([]);
  const projectsRequestIdRef = useRef(0);

  useEffect(() => {
    if (isOpen) {
      if (task) {
        // Edit mode
        setTitle(task.title);
        setDescription(task.description ?? "");
        setProjectId(task.projectId);
        setPriority(task.priority ?? TaskPriority.MEDIUM);
        setStatus(task.status ?? TaskStatus.TODO);
        setType(task.type ?? TaskType.FEATURE);
        setDueDate(
          task.dueDate
            ? new Date(task.dueDate).toISOString().split("T")[0]
            : "",
        );

      } else {
        // Create mode - reset fields
        setTitle("");
        setDescription("");
        setProjectId(defaultProjectId ?? "");
        setPriority(TaskPriority.MEDIUM);
        setStatus(TaskStatus.TODO);
        setType(TaskType.FEATURE);
        setDueDate("");

      }
      setError(null);
    }
  }, [isOpen, task, defaultProjectId]);

  useEffect(() => {
    if (isOpen && !defaultProjectId && !task) {
      const cachedProjects = projectsCache;
      if (cachedProjects && cachedProjects.expiresAt > Date.now()) {
        setProjects(cachedProjects.data);
        return;
      }

      let cancelled = false;
      const cacheGeneration = projectsCacheGeneration;
      const requestId = projectsRequestIdRef.current + 1;
      projectsRequestIdRef.current = requestId;

      // Fetch projects if not provided and not editing
      const fetchProjects = async () => {
        try {
          const response = await projectsApi.getProjects();
          if (
            cancelled ||
            requestId !== projectsRequestIdRef.current ||
            cacheGeneration !== projectsCacheGeneration
          ) {
            return;
          }
          const data = Array.isArray(response)
            ? response
            : ((response as Record<string, unknown>).data as Project[]) ?? [];
          projectsCache = {
            data,
            expiresAt: Date.now() + PROJECT_CACHE_TTL_MS,
          };
          setProjects(data);
        } catch (err) {
          if (!cancelled && requestId === projectsRequestIdRef.current) {
            console.error("Failed to fetch projects", err);
          }
        }
      };
      fetchProjects();

      return () => {
        cancelled = true;
      };
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
      const taskData: UpdateTaskRequest = {
        title,
        description,
        priority: priority as TaskPriority,
        status: status as TaskStatus,
        type: type as TaskType,
        dueDate: dueDate ? new Date(dueDate).toISOString() : undefined,
      };

      if (task) {
        // Update existing task
        await tasksApi.updateTask(task.id, taskData);
      } else {
        // Create new task
        const createData: CreateTaskRequest = {
          title,
          description,
          projectId,
          priority: priority as TaskPriority,
          type: type as TaskType,
          dueDate: taskData.dueDate,
        };
        await tasksApi.createTask(projectId, createData);
      }
      onTaskCreated();
      toast.success(task ? "Task updated successfully" : "Task created successfully");
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

      }
    } catch (err) {
      console.error("Failed to save task", err);
      setError("Failed to save task. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  const projectOptions = useMemo(
    () => projects.map((p) => ({ value: p.id, label: p.name })),
    [projects],
  );

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

  const priorityOptions = useMemo(
    () =>
      Object.values(TaskPriority).map((p) => ({
        value: p,
        label: p.charAt(0).toUpperCase() + p.slice(1).replace("_", " "),
        color: getPriorityColor(p),
      })),
    [],
  );

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

  const statusOptions = useMemo(
    () =>
      Object.values(TaskStatus).map((s) => ({
        value: s,
        label: s.charAt(0).toUpperCase() + s.slice(1).replace("_", " "),
        color: getStatusColor(s),
      })),
    [],
  );

  const typeOptions = useMemo(
    () =>
      Object.values(TaskType).map((t) => ({
        value: t,
        label: t.charAt(0).toUpperCase() + t.slice(1).replace("_", " "),
        color: "text-muted-foreground",
      })),
    [],
  );

  let submitLabel = "Create Task";
  if (task) {
    submitLabel = "Save Changes";
  }
  if (loading) {
    submitLabel = task ? "Saving..." : "Creating...";
  }

  return (
    <AnimatedModalShell
      isOpen={isOpen}
      onClose={onClose}
      containerClassName="sm:p-6"
      className="relative w-full max-w-lg rounded-2xl border border-border bg-popover/95 backdrop-blur-xl shadow-2xl max-h-[90vh] overflow-y-auto"
    >
            {/* Header */}
            <div className="flex items-center justify-between px-6 py-4 border-b border-border bg-accent/20 sticky top-0 z-10 backdrop-blur-md">
              <div className="flex items-center gap-2">
                <Layout className="h-5 w-5 text-primary" />
                <h2 className="text-lg font-semibold text-foreground">
                  {task ? "Edit Task" : "Create New Task"}
                </h2>
              </div>
              <Button
                variant="ghost"
                size="icon"
                onClick={onClose}
                className="h-8 w-8 text-muted-foreground hover:text-foreground rounded-full hover:bg-accent transition-colors cursor-pointer"
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
                    <label htmlFor={`${id}-title`} className="text-xs font-medium text-muted-foreground ml-1 uppercase tracking-wider">
                      Title
                    </label>
                    <Input
                      id={`${id}-title`}
                      name="title"
                      autoComplete="off"
                      value={title}
                      onChange={(e) => setTitle(e.target.value)}
                      placeholder="What needs to be done?"
                      className="bg-muted/50 border-border text-foreground placeholder:text-muted-foreground/50 focus-visible:ring-primary/50 text-lg py-6"
                      autoFocus={!task}
                    />
                  </div>

                  <div className="space-y-1.5">
                    <label htmlFor={`${id}-description`} className="text-xs font-medium text-muted-foreground ml-1 uppercase tracking-wider">
                      Description
                    </label>
                    <Textarea
                      id={`${id}-description`}
                      name="description"
                      autoComplete="off"
                      value={description}
                      onChange={(e) => setDescription(e.target.value)}
                      placeholder="Add details, context, and acceptance criteria..."
                      className="min-h-[120px] bg-muted/50 border-border text-foreground placeholder:text-muted-foreground/50 focus-visible:ring-primary/50 resize-none"
                    />
                  </div>
                </div>

                {/* Meta Fields Grid */}
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 pt-2">
                  {!defaultProjectId && !task && (
                    <div className="space-y-1.5 col-span-2">
                      <div className="flex items-center gap-2 text-xs font-medium text-muted-foreground ml-1 uppercase tracking-wider">
                        <Briefcase className="h-3 w-3" />
                        <label htmlFor={`${id}-project`}>Project</label>
                      </div>
                      <CustomSelect
                        id={`${id}-project`}
                        name="project"
                        value={projectId}
                        onChange={setProjectId}
                        options={projectOptions}
                        className="w-full"
                      />
                    </div>
                  )}

                  <div className="space-y-1.5">
                    <div className="flex items-center gap-2 text-xs font-medium text-muted-foreground ml-1 uppercase tracking-wider">
                      <Flag className="h-3 w-3" />
                      <label htmlFor={`${id}-priority`}>Priority</label>
                    </div>
                    <CustomSelect
                      id={`${id}-priority`}
                      name="priority"
                      value={priority}
                      onChange={setPriority}
                      options={priorityOptions}
                      className="w-full"
                    />
                  </div>

                  <div className="space-y-1.5">
                    <div className="flex items-center gap-2 text-xs font-medium text-muted-foreground ml-1 uppercase tracking-wider">
                      <CheckCircle2 className="h-3 w-3" />
                      <label htmlFor={`${id}-status`}>Status</label>
                    </div>
                    <CustomSelect
                      id={`${id}-status`}
                      name="status"
                      value={status}
                      onChange={setStatus}
                      options={statusOptions}
                      className="w-full"
                    />
                  </div>

                  <div className="space-y-1.5">
                    <div className="flex items-center gap-2 text-xs font-medium text-muted-foreground ml-1 uppercase tracking-wider">
                      <Tag className="h-3 w-3" />
                      <label htmlFor={`${id}-type`}>Type</label>
                    </div>
                    <CustomSelect
                      id={`${id}-type`}
                      name="type"
                      value={type}
                      onChange={setType}
                      options={typeOptions}
                      className="w-full"
                    />
                  </div>

                  <div className="space-y-1.5">
                    <div className="flex items-center gap-2 text-xs font-medium text-muted-foreground ml-1 uppercase tracking-wider">
                      <Calendar className="h-3 w-3" />
                      <label htmlFor={`${id}-due-date`}>Due Date</label>
                    </div>
                    <div className="relative">
                      <Input
                        id={`${id}-due-date`}
                        name="dueDate"
                        autoComplete="off"
                        type="date"
                        value={dueDate}
                        onChange={(e) => setDueDate(e.target.value)}
                        className="w-full h-9 px-3 py-2 bg-background border-border rounded-lg text-sm text-foreground focus:ring-2 focus:ring-primary/50 dark:[&::-webkit-calendar-picker-indicator]:invert dark:[&::-webkit-calendar-picker-indicator]:opacity-50 dark:[&::-webkit-calendar-picker-indicator]:cursor-pointer dark:[&::-webkit-calendar-picker-indicator]:hover:opacity-100 transition-colors"
                      />
                    </div>
                  </div>
                </div>

                {/* Actions */}
                <div className="flex items-center justify-end gap-3 pt-6 border-t border-border">
                  <Button
                    type="button"
                    variant="ghost"
                    onClick={onClose}
                    className="text-muted-foreground hover:text-foreground hover:bg-accent"
                  >
                    Cancel
                  </Button>
                  <Button
                    type="submit"
                    disabled={loading}
                    className="bg-primary hover:bg-primary/90 text-primary-foreground shadow-lg shadow-primary/20"
                  >
                    {submitLabel}
                  </Button>
                </div>
              </form>
            </div>
    </AnimatedModalShell>
  );
}
