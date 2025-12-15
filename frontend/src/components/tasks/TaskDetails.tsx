"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { CustomSelect } from "@/components/ui/custom-select";
import {
  ArrowLeft,
  Calendar,
  User as UserIcon,
  Clock,
  MoreVertical,
  Pencil,
  Trash,
  Tag,
  History,
  Flag,
  // CheckCircle2,
  // Timer,
  Save,
  X,
  Briefcase,
} from "lucide-react";
import { format } from "date-fns";
import type { Task } from "@/types";
import { TaskStatus, TaskPriority, TaskType } from "@/types";
import { tasksApi } from "@/lib/api-endpoints";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { motion, AnimatePresence } from "framer-motion";
import { toast } from "sonner";

interface TaskDetailsProps {
  task: Task;
  backLink: string;
  backLabel: string;
}

const renderDescription = (text: string) => {
  if (!text) {
    return (
      <span className="text-zinc-600 italic">No description provided.</span>
    );
  }

  const lines = text.split("\n");
  const elements: JSX.Element[] = [];
  let listBuffer: JSX.Element[] = [];
  let inList = false;
  let listType = "ul";

  lines.forEach((line, index) => {
    const trimmed = line.trim();
    const isBullet = trimmed.startsWith("- ") || trimmed.startsWith("* ");
    const isNumber = /^\d+\.\s/.test(trimmed);

    if (isBullet || isNumber) {
      if (!inList) {
        inList = true;
        listType = isNumber ? "ol" : "ul";
      }
      const content = trimmed.replace(/^[-*] |\d+\.\s/, "");
      listBuffer.push(
        <li key={`li-${index}`} className="ml-4 pl-1">
          {content}
        </li>,
      );
    } else {
      if (inList) {
        elements.push(
          listType === "ul" ? (
            <ul key={`ul-${index}`} className="list-disc mb-4 space-y-1">
              {listBuffer}
            </ul>
          ) : (
            <ol key={`ol-${index}`} className="list-decimal mb-4 space-y-1">
              {listBuffer}
            </ol>
          ),
        );
        listBuffer = [];
        inList = false;
      }
      if (trimmed) {
        elements.push(
          <p key={`p-${index}`} className="mb-2 min-h-[1.5em]">
            {line}
          </p>,
        );
      } else {
        elements.push(<br key={`br-${index}`} />);
      }
    }
  });
  if (inList && listBuffer.length > 0) {
    elements.push(
      listType === "ul" ? (
        <ul key="ul-last" className="list-disc mb-4 space-y-1">
          {listBuffer}
        </ul>
      ) : (
        <ol key="ol-last" className="list-decimal mb-4 space-y-1">
          {listBuffer}
        </ol>
      ),
    );
  }
  return (
    <div className="text-zinc-300 leading-relaxed text-[15px]">{elements}</div>
  );
};

export function TaskDetails({
  task: initialTask,
  backLink,
  backLabel,
}: TaskDetailsProps) {
  const router = useRouter();
  const [task, setTask] = useState<Task>(initialTask);
  const [isEditing, setIsEditing] = useState(false);
  const [isDeleteModalOpen, setIsDeleteModalOpen] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);

  // Edit State
  const [title, setTitle] = useState(task.title);
  const [description, setDescription] = useState(task.description ?? "");
  const [priority, setPriority] = useState<TaskPriority>(task.priority);
  const [status, setStatus] = useState<TaskStatus>(task.status);
  const [type, setType] = useState<TaskType>(task.type);
  const [tags, setTags] = useState(task.tags ? task.tags.join(", ") : "");
  const [dueDate, setDueDate] = useState(
    task.dueDate ? new Date(task.dueDate).toISOString().split("T")[0] : "",
  );
  const [estimatedHours, setEstimatedHours] = useState(
    task.estimatedHours?.toString() ?? "",
  );
  const [actualHours, setActualHours] = useState(
    task.actualHours?.toString() ?? "",
  );

  useEffect(() => {
    setTask(initialTask);
  }, [initialTask]);

  // Sync edit state when task changes or mode toggles
  useEffect(() => {
    if (isEditing) {
      setTitle(task.title);
      setDescription(task.description ?? "");
      setPriority(task.priority);
      setStatus(task.status);
      setType(task.type);
      setTags(task.tags ? task.tags.join(", ") : "");
      setDueDate(
        task.dueDate ? new Date(task.dueDate).toISOString().split("T")[0] : "",
      );
      setEstimatedHours(task.estimatedHours?.toString() ?? "");
      setActualHours(task.actualHours?.toString() ?? "");
    }
  }, [isEditing, task]);

  const handleSave = async () => {
    // Create a backup of the current task state
    const previousTask = task;

    try {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const taskData: any = {
        title,
        description,
        priority,
        status,
        type,
        tags: tags
          .split(",")
          .map((t) => t.trim())
          .filter(Boolean),
        dueDate: dueDate ? new Date(dueDate).toISOString() : undefined,
        estimatedHours: estimatedHours ? parseFloat(estimatedHours) : undefined,
        actualHours: actualHours ? parseFloat(actualHours) : undefined,
      };

      // 1. Optimistic Update: Update UI immediately
      const optimisticTask = {
        ...task,
        ...taskData,
        updatedAt: new Date().toISOString(), // Fake update time for immediate feedback
      };

      setTask(optimisticTask);
      setIsEditing(false);
      toast.success("Task updated successfully");

      // 2. Send request to server in background
      const updated = await tasksApi.updateTask(task.id, taskData);

      // 3. Confirm with actual server data (silent update)
      setTask(updated);
    } catch (error) {
      console.error("Failed to save task:", error);
      // 4. Revert on failure
      setTask(previousTask);
      setIsEditing(true);
      toast.error("Failed to update task");
    }
  };

  const handleDelete = async () => {
    setIsDeleting(true);
    try {
      await tasksApi.deleteTask(task.id);
      toast.success("Task deleted successfully");
      router.push(backLink);
      router.refresh();
    } catch (error) {
      console.error("Failed to delete task:", error);
      setIsDeleting(false);
      toast.error("Failed to delete task");
    }
  };

  const getStatusColor = (s: string) => {
    switch (s) {
      case TaskStatus.DONE:
        return "bg-emerald-500/10 text-emerald-400 border-emerald-500/20";
      case TaskStatus.IN_PROGRESS:
        return "bg-blue-500/10 text-blue-400 border-blue-500/20";
      case TaskStatus.IN_REVIEW:
        return "bg-purple-500/10 text-purple-400 border-purple-500/20";
      case TaskStatus.CANCELLED:
        return "bg-red-500/10 text-red-400 border-red-500/20";
      case TaskStatus.TODO:
      default:
        return "bg-zinc-500/10 text-zinc-400 border-zinc-500/20";
    }
  };

  const getPriorityColor = (p: string) => {
    switch (p) {
      case TaskPriority.URGENT:
        return "text-fuchsia-400 bg-fuchsia-400/10 border-fuchsia-400/20";
      case TaskPriority.HIGH:
        return "text-red-400 bg-red-400/10 border-red-400/20";
      case TaskPriority.MEDIUM:
        return "text-amber-400 bg-amber-400/10 border-amber-400/20";
      case TaskPriority.LOW:
        return "text-green-400 bg-green-400/10 border-green-400/20";
      default:
        return "text-zinc-400 bg-zinc-400/10 border-zinc-400/20";
    }
  };

  // Options for Selects
  const priorityOptions = Object.values(TaskPriority).map((p) => ({
    value: p,
    label: p.charAt(0).toUpperCase() + p.slice(1),
    color: getPriorityColor(p),
  }));
  const statusOptions = Object.values(TaskStatus).map((s) => ({
    value: s,
    label: s.replace("_", " ").replace(/\b\w/g, (c) => c.toUpperCase()),
    color: getStatusColor(s),
  }));
  const typeOptions = Object.values(TaskType).map((t) => ({
    value: t,
    label: t.charAt(0).toUpperCase() + t.slice(1),
    color: "text-zinc-400",
  }));

  return (
    <div className="space-y-6 max-w-6xl mx-auto">
      {/* Back Button */}
      <Link href={backLink} passHref>
        <Button
          variant="ghost"
          size="sm"
          className="p-0 h-auto hover:bg-transparent text-zinc-400 hover:text-white mb-2"
        >
          <ArrowLeft className="h-4 w-4 mr-1" />
          {backLabel}
        </Button>
      </Link>

      {/* Main Content Area */}
      <div className="bg-[#18181b]/50 backdrop-blur-xl border border-white/10 rounded-2xl p-6 md:p-8 relative">
        {/* Top Actions (Edit/Delete) */}
        <div className="absolute top-6 right-6 flex items-center gap-2">
          {isEditing ? (
            <>
              <Button
                size="sm"
                variant="ghost"
                onClick={() => setIsEditing(false)}
                className="text-zinc-400 hover:text-white"
              >
                <X className="h-4 w-4 mr-1" /> Cancel
              </Button>
              <Button
                size="sm"
                onClick={handleSave}
                className="bg-indigo-600 hover:bg-indigo-700 text-white"
              >
                <Save className="h-4 w-4 mr-1" /> Save
              </Button>
            </>
          ) : (
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-8 w-8 text-zinc-400 hover:text-white hover:bg-white/10"
                >
                  <MoreVertical className="h-4 w-4" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent
                align="end"
                className="w-48 bg-[#18181b] border-white/10 z-50"
              >
                <DropdownMenuItem
                  onClick={() => setIsEditing(true)}
                  className="text-zinc-300 hover:text-white hover:bg-white/10 cursor-pointer"
                >
                  <Pencil className="h-4 w-4 mr-2" />
                  Edit Task
                </DropdownMenuItem>
                <DropdownMenuSeparator className="bg-white/10" />
                <DropdownMenuItem
                  onClick={() => setIsDeleteModalOpen(true)}
                  className="text-red-400 hover:text-red-300 hover:bg-red-500/10 cursor-pointer"
                >
                  <Trash className="h-4 w-4 mr-2" />
                  Delete Task
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          )}
        </div>

        <div className="flex flex-col gap-4 max-w-4xl">
          {/* 1. Title (Moved to Top) */}
          <div className="mt-2">
            {isEditing ? (
              <Input
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                className="text-2xl md:text-3xl font-bold bg-black/20 border-white/10 text-white h-auto py-2"
              />
            ) : (
              <h1 className="text-3xl md:text-4xl font-bold text-white leading-tight">
                {task.title}
              </h1>
            )}
          </div>

          {/* 2. Project Name, Priority, Type, Assignee, Status (Below Title) */}
          <div className="flex flex-col md:flex-row md:items-center gap-3 md:gap-4 text-sm flex-wrap text-zinc-400">
            {/* Project Name */}
            <div className="flex items-center gap-2 font-medium tracking-wide text-zinc-500">
              <Briefcase className="h-4 w-4" />
              {task.project?.name ?? "Project"}
            </div>

            {/* Metadata Items */}
            <div className="flex items-center gap-3 flex-wrap">
              {isEditing ? (
                <>
                  <div className="w-32">
                    <CustomSelect
                      value={priority}
                      onChange={(v) => setPriority(v as TaskPriority)}
                      options={priorityOptions}
                      className="w-full"
                    />
                  </div>
                  <div className="w-32">
                    <CustomSelect
                      value={type}
                      onChange={(v) => setType(v as TaskType)}
                      options={typeOptions}
                      className="w-full"
                    />
                  </div>
                  <div className="w-40">
                    <CustomSelect
                      value={status}
                      onChange={(v) => setStatus(v as TaskStatus)}
                      options={statusOptions}
                      className="w-full"
                    />
                  </div>
                </>
              ) : (
                <>
                  {/* Priority */}
                  <span
                    className={`flex items-center gap-1.5 ${getPriorityColor(task.priority).split(" ")[0]}`}
                  >
                    <Flag className="h-3.5 w-3.5" />
                    <span className="capitalize">{task.priority}</span>
                  </span>

                  {/* Type */}
                  <span className="flex items-center gap-1.5 hover:text-zinc-300 transition-colors">
                    <Tag className="h-3.5 w-3.5" />
                    <span className="capitalize">{task.type ?? "Feature"}</span>
                  </span>

                  {/* Assignee */}
                  <span className="flex items-center gap-1.5 text-zinc-400 hover:text-zinc-300 transition-colors">
                    <UserIcon className="h-3.5 w-3.5" />
                    {task.assignee?.firstName
                      ? `${task.assignee?.firstName} ${task.assignee?.lastName ?? ""}`.trim()
                      : (task.assignee?.username ?? "Unassigned")}
                  </span>

                  {/* Status (Badge Style for prominence) */}
                  <Badge
                    className={`${getStatusColor(task.status)} border px-2.5 py-0.5 text-xs uppercase tracking-wider ml-2`}
                  >
                    {task.status.replace("_", " ")}
                  </Badge>
                </>
              )}
            </div>
          </div>
        </div>

        {/* Divider */}
        <div className="h-px w-full bg-white/5 my-8"></div>

        <div className="grid gap-8 md:grid-cols-3">
          {/* Main Content */}
          <div className="md:col-span-2 space-y-8">
            <div>
              <h3 className="text-lg font-semibold text-white mb-4">
                Description
              </h3>
              {isEditing ? (
                <Textarea
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  className="bg-black/20 border-white/10 text-white min-h-[200px]"
                />
              ) : (
                renderDescription(task.description ?? "")
              )}
            </div>
          </div>

          {/* Sidebar Details */}
          <div className="space-y-6">
            <Card className="border-0 bg-transparent shadow-none p-0">
              <CardHeader className="px-0 pt-0">
                <CardTitle className="text-xs font-semibold text-zinc-400 uppercase tracking-wider">
                  Details
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-6 px-0">
                {/* Due Date */}
                <div className="flex items-start gap-3">
                  <Calendar className="h-4 w-4 text-zinc-500 mt-1" />
                  <div className="flex-1">
                    <p className="text-xs text-zinc-500 mb-0.5">Due Date</p>
                    {isEditing ? (
                      <Input
                        type="date"
                        value={dueDate}
                        onChange={(e) => setDueDate(e.target.value)}
                        className="bg-black/20 border-white/10 text-white h-8 text-xs"
                      />
                    ) : (
                      <p className="text-sm text-zinc-300 font-medium">
                        {task.dueDate
                          ? format(new Date(task.dueDate), "MMM d, yyyy")
                          : "No due date"}
                      </p>
                    )}
                  </div>
                </div>

                {/* Created At */}
                <div className="flex items-start gap-3">
                  <Clock className="h-4 w-4 text-zinc-500 mt-1" />
                  <div className="flex-1">
                    <p className="text-xs text-zinc-500 mb-0.5">Created</p>
                    <p className="text-sm text-zinc-300">
                      {format(new Date(task.createdAt), "MMM d, yyyy")}
                    </p>
                  </div>
                </div>

                {/* Last Updated */}
                <div className="flex items-start gap-3">
                  <History className="h-4 w-4 text-zinc-500 mt-1" />
                  <div className="flex-1">
                    <p className="text-xs text-zinc-500 mb-0.5">Last Updated</p>
                    <p className="text-sm text-zinc-300">
                      {format(new Date(task.updatedAt), "MMM d, yyyy")}
                    </p>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
        </div>
      </div>

      {/* Delete Confirmation Modal */}
      <AnimatePresence>
        {isDeleteModalOpen && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm">
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.95 }}
              className="bg-[#18181b] border border-white/10 rounded-xl p-6 max-w-sm w-full shadow-2xl"
            >
              <h3 className="text-lg font-bold text-white mb-2">
                Delete Task?
              </h3>
              <p className="text-zinc-400 text-sm mb-6">
                Are you sure you want to delete{" "}
                <span className="text-white font-medium">"{task.title}"</span>?
                This action cannot be undone.
              </p>
              <div className="flex justify-end gap-3">
                <Button
                  variant="ghost"
                  onClick={() => setIsDeleteModalOpen(false)}
                  className="text-zinc-400 hover:text-white hover:bg-white/5"
                >
                  Cancel
                </Button>
                <Button
                  onClick={handleDelete}
                  disabled={isDeleting}
                  className="bg-red-500/10 text-red-500 hover:bg-red-500/20 hover:text-red-400"
                >
                  {isDeleting ? "Deleting..." : "Delete Task"}
                </Button>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </div>
  );
}
