"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { cn } from "@/lib/utils";

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
  MessageSquare,
  Send,
  // CheckCircle2,
  // Timer,
  Save,
  X,
  Briefcase,
} from "lucide-react";
import { format } from "date-fns";
import type { Task, TaskComment } from "@/types";
import { TaskStatus, TaskPriority, TaskType } from "@/types";
import {
  buildTaskUpdateRequest,
  getDueDateBadgeColor,
  getDueDateIconColor,
  getDueDateLabel,
  renderDescription,
} from "./task-details-helpers";
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

interface TaskDeleteDialogProps {
  readonly open: boolean;
  readonly taskTitle: string;
  readonly isDeleting: boolean;
  readonly onClose: () => void;
  readonly onDelete: () => void;
}

function TaskDeleteDialog({
  open,
  taskTitle,
  isDeleting,
  onClose,
  onDelete,
}: TaskDeleteDialogProps) {
  return (
    <AnimatePresence>
      {open && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm">
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.95 }}
            className="bg-popover border border-border rounded-xl p-6 max-w-sm w-full shadow-2xl"
          >
            <h3 className="text-lg font-bold text-foreground mb-2">Delete Task?</h3>
            <p className="text-muted-foreground text-sm mb-6">
              Are you sure you want to delete{" "}
              <span className="text-foreground font-medium">"{taskTitle}"</span>?
              This action cannot be undone.
            </p>
            <div className="flex justify-end gap-3">
              <Button
                variant="ghost"
                onClick={onClose}
                className="text-muted-foreground hover:text-foreground hover:bg-accent"
              >
                Cancel
              </Button>
              <Button
                onClick={onDelete}
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
  );
}

export function TaskDetails({
  task: initialTask,
  backLink,
  backLabel,
}: Readonly<TaskDetailsProps>) {
  const router = useRouter();
  const [task, setTask] = useState<Task>(initialTask);
  const [isEditing, setIsEditing] = useState(false);
  const [isDeleteModalOpen, setIsDeleteModalOpen] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  const [comments, setComments] = useState<TaskComment[]>(initialTask.comments ?? []);
  const [isCommentsLoading, setIsCommentsLoading] = useState(false);
  const [commentDraft, setCommentDraft] = useState("");
  const [isSubmittingComment, setIsSubmittingComment] = useState(false);

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
    setComments(initialTask.comments ?? []);
  }, [initialTask]);

  useEffect(() => {
    let isMounted = true;

    const loadComments = async () => {
      try {
        setIsCommentsLoading(true);
        const fetchedComments = await tasksApi.getTaskComments(initialTask.id);
        if (isMounted) {
          setComments(fetchedComments);
        }
      } catch (error) {
        console.error("Failed to load task comments:", error);
      } finally {
        if (isMounted) {
          setIsCommentsLoading(false);
        }
      }
    };

    void loadComments();

    return () => {
      isMounted = false;
    };
  }, [initialTask.id]);

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
      const taskData = buildTaskUpdateRequest({
        title,
        description,
        priority,
        status,
        type,
        tags,
        dueDate,
        estimatedHours,
        actualHours,
      });

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

  const handleCommentSubmit = async () => {
    const content = commentDraft.trim();
    if (!content) {
      return;
    }

    try {
      setIsSubmittingComment(true);
      const createdComment = await tasksApi.createTaskComment(task.id, { content });
      setComments((current) => [...current, createdComment]);
      setCommentDraft("");
      toast.success("Comment posted");
    } catch (error) {
      console.error("Failed to post comment:", error);
      toast.error("Failed to post comment");
    } finally {
      setIsSubmittingComment(false);
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

  const getStatusTextColor = (s: string) => {
    switch (s) {
      case TaskStatus.DONE:
        return "text-emerald-500 dark:text-emerald-400";
      case TaskStatus.IN_PROGRESS:
        return "text-blue-500 dark:text-blue-400";
      case TaskStatus.IN_REVIEW:
        return "text-purple-500 dark:text-purple-400";
      case TaskStatus.CANCELLED:
        return "text-red-500 dark:text-red-400";
      case TaskStatus.TODO:
      default:
        return "text-zinc-500 dark:text-zinc-400";
    }
  };

  const getPriorityTextColor = (p: string) => {
    switch (p) {
      case TaskPriority.URGENT:
        return "text-fuchsia-500 dark:text-fuchsia-400";
      case TaskPriority.HIGH:
        return "text-red-500 dark:text-red-400";
      case TaskPriority.MEDIUM:
        return "text-amber-500 dark:text-amber-400";
      case TaskPriority.LOW:
        return "text-green-500 dark:text-green-400";
      default:
        return "text-zinc-500 dark:text-zinc-400";
    }
  };

  // Options for Selects
  const priorityOptions = Object.values(TaskPriority).map((p) => ({
    value: p,
    label: p.charAt(0).toUpperCase() + p.slice(1),
    color: getPriorityTextColor(p),
  }));
  const statusOptions = Object.values(TaskStatus).map((s) => ({
    value: s,
    label: s.replace("_", " ").replace(/\b\w/g, (c) => c.toUpperCase()),
    color: getStatusTextColor(s),
  }));
  const typeOptions = Object.values(TaskType).map((t) => ({
    value: t,
    label: t.charAt(0).toUpperCase() + t.slice(1),
    color: "text-zinc-500 dark:text-zinc-400",
  }));

  return (
    <div className="space-y-6 max-w-6xl mx-auto">
      {/* Back Button */}
      <Link href={backLink} passHref>
        <Button
          variant="ghost"
          size="sm"
          className="p-0 h-auto hover:bg-transparent text-muted-foreground hover:text-foreground mb-2"
        >
          <ArrowLeft className="h-4 w-4 mr-1" />
          {backLabel}
        </Button>
      </Link>

      {/* Main Content Area */}
      <div className="bg-card/50 backdrop-blur-xl border border-border rounded-2xl p-6 md:p-8 relative">
        {/* Header Section */}
        <div className="space-y-6">
          {/* Top Row: Project Breadcrumb & Actions */}
          <div className="flex items-center justify-between gap-4">
            {/* Project Name */}
            <div className="flex items-center gap-2 text-sm font-medium text-muted-foreground/80 bg-secondary/50 px-3 py-1.5 rounded-full w-fit">
              <Briefcase className="h-3.5 w-3.5" />
              {task.project?.name ?? "Project"}
            </div>

            {/* Actions (Edit/Delete/Save) */}
            <div className="flex items-center gap-2 text-right">
              {isEditing ? (
                <>
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={() => setIsEditing(false)}
                    className="text-muted-foreground hover:text-foreground h-8"
                  >
                    <X className="h-4 w-4 mr-1" /> <span className="hidden sm:inline">Cancel</span>
                  </Button>
                  <Button
                    size="sm"
                    onClick={handleSave}
                    className="bg-primary hover:bg-primary/90 text-primary-foreground h-8 min-w-[80px]"
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
                      className="h-8 w-8 text-muted-foreground hover:text-foreground hover:bg-accent"
                    >
                      <MoreVertical className="h-4 w-4" />
                    </Button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent
                    align="end"
                    className="w-48 bg-popover border-border z-50"
                  >
                    <DropdownMenuItem
                      onClick={() => setIsEditing(true)}
                      className="text-foreground hover:bg-accent cursor-pointer"
                    >
                      <Pencil className="h-4 w-4 mr-2" />
                      Edit Task
                    </DropdownMenuItem>
                    <DropdownMenuSeparator className="bg-border" />
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
          </div>

          {/* Title Row */}
          <div>
            {isEditing ? (
              <>
                <label htmlFor="task-detail-title" className="sr-only">Task Title</label>
                <Input
                  id="task-detail-title"
                  name="title"
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  placeholder="Task Title"
                  autoComplete="off"
                  aria-label="Task Title"
                  className="text-2xl md:text-3xl font-bold bg-transparent border-none px-0 shadow-none focus-visible:ring-0 placeholder:text-muted-foreground/30 h-auto py-1"
                />
              </>
            ) : (
              <h1 className="text-3xl md:text-4xl font-bold text-foreground leading-tight tracking-tight">
                {task.title}
              </h1>
            )}
          </div>

          {/* Metadata Row (Status, Priority, Type, Assignee) */}
          <div className="flex flex-wrap items-center gap-4">
            {isEditing ? (
              <>
                <div className="w-40">
                  <CustomSelect
                    value={status}
                    onChange={(v) => setStatus(v as TaskStatus)}
                    options={statusOptions}
                    className="w-full h-9"
                  />
                </div>
                <div className="w-36">
                  <CustomSelect
                    value={priority}
                    onChange={(v) => setPriority(v as TaskPriority)}
                    options={priorityOptions}
                    className="w-full h-9"
                  />
                </div>
                <div className="w-36">
                  <CustomSelect
                    value={type}
                    onChange={(v) => setType(v as TaskType)}
                    options={typeOptions}
                    className="w-full h-9"
                  />
                </div>
              </>
            ) : (
              <>
                {/* Status Badge */}
                <Badge
                  className={`${getStatusColor(task.status)} border px-3 py-1 text-xs font-semibold uppercase tracking-wide rounded-md`}
                >
                  {task.status.replace("_", " ")}
                </Badge>

                {/* Priority */}
                <div
                  className={`flex items-center gap-1.5 px-2.5 py-1 rounded-md border text-xs font-medium ${getPriorityColor(task.priority)}`}
                >
                  <Flag className="h-3.5 w-3.5" />
                  <span className="capitalize">{task.priority}</span>
                </div>

                {/* Type */}
                <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-md border text-xs font-medium text-muted-foreground bg-secondary/30 border-border">
                  <Tag className="h-3.5 w-3.5" />
                  <span className="capitalize">{task.type ?? "Feature"}</span>
                </div>
              </>
            )}

            {/* Separator */}
            <div className="h-6 w-px bg-border mx-1 hidden sm:block"></div>

            {/* Assignee */}
            <div className="flex items-center gap-2 text-sm text-muted-foreground bg-secondary/20 px-3 py-1.5 rounded-full border border-border/50">
              <UserIcon className="h-3.5 w-3.5" />
              <span>
                {task.assignee?.firstName
                  ? `${task.assignee?.firstName} ${task.assignee?.lastName ?? ""}`.trim()
                  : (task.assignee?.username ?? "Unassigned")}
              </span>
            </div>
          </div>
        </div>

        {/* Divider */}
        <div className="h-px w-full bg-border my-8"></div>

        <div className="grid gap-8 md:grid-cols-3">
          {/* Main Content */}
          <div className="md:col-span-2 space-y-8">
            <div>
              <h3 className="text-lg font-semibold text-foreground mb-4">
                Description
              </h3>
              {isEditing ? (
                <>
                  <label htmlFor="task-detail-description" className="sr-only">Description</label>
                  <Textarea
                    id="task-detail-description"
                    name="description"
                    value={description}
                    onChange={(e) => setDescription(e.target.value)}
                    autoComplete="off"
                    aria-label="Description"
                    className="bg-background border-border text-foreground min-h-[200px]"
                  />
                </>
              ) : (
                renderDescription(task.description ?? "")
              )}
            </div>

            <div>
              <div className="flex items-center justify-between gap-3 mb-4">
                <div>
                  <h3 className="text-lg font-semibold text-foreground flex items-center gap-2">
                    <MessageSquare className="h-4 w-4 text-primary" />
                    Comments
                  </h3>
                  <p className="text-xs text-muted-foreground mt-1">
                    Use <span className="font-mono">@username</span> to mention teammates.
                  </p>
                </div>
                <div className="text-xs text-muted-foreground">
                  {comments.length} comment{comments.length === 1 ? "" : "s"}
                </div>
              </div>

              <div className="space-y-4">
                <div className="rounded-xl border border-border bg-background/60 p-4 space-y-3">
                  <Textarea
                    value={commentDraft}
                    onChange={(event) => setCommentDraft(event.target.value)}
                    placeholder="Add a comment or mention someone with @username"
                    className="min-h-[110px] bg-transparent border-border"
                    disabled={isSubmittingComment}
                  />
                  <div className="flex items-center justify-between gap-3">
                    <p className="text-xs text-muted-foreground">
                      Mention notifications are sent when the username matches an active account.
                    </p>
                    <Button
                      type="button"
                      onClick={handleCommentSubmit}
                      disabled={!commentDraft.trim() || isSubmittingComment}
                      className="bg-primary hover:bg-primary/90 text-primary-foreground"
                    >
                      <Send className="h-4 w-4 mr-2" />
                      {isSubmittingComment ? "Posting..." : "Post Comment"}
                    </Button>
                  </div>
                </div>

                <div className="space-y-3">
                  {isCommentsLoading && (
                    <div className="rounded-xl border border-border bg-background/40 px-4 py-6 text-sm text-muted-foreground">
                      Loading comments...
                    </div>
                  )}
                  {!isCommentsLoading && comments.length === 0 && (
                    <div className="rounded-xl border border-dashed border-border bg-background/30 px-4 py-6 text-sm text-muted-foreground">
                      No comments yet. Start the discussion here.
                    </div>
                  )}
                  {!isCommentsLoading && comments.length > 0 && (
                    comments.map((comment) => (
                      <div
                        key={comment.id}
                        className="rounded-xl border border-border bg-background/40 p-4 space-y-2"
                      >
                        <div className="flex items-start justify-between gap-3">
                          <div>
                            <p className="text-sm font-medium text-foreground">
                              {comment.user.firstName
                                ? `${comment.user.firstName} ${comment.user.lastName ?? ""}`.trim()
                                : (comment.user.username ?? comment.user.email)}
                            </p>
                            <p className="text-xs text-muted-foreground">
                              {format(new Date(comment.createdAt), "MMM d, yyyy h:mm a")}
                            </p>
                          </div>
                          {comment.mentions.length > 0 && (
                            <div className="text-[11px] uppercase tracking-wide text-amber-400">
                              {comment.mentions.length} mention{comment.mentions.length === 1 ? "" : "s"}
                            </div>
                          )}
                        </div>
                        <p className="text-sm leading-relaxed text-muted-foreground whitespace-pre-wrap">
                          {comment.content}
                        </p>
                      </div>
                    ))
                  )}
                </div>
              </div>
            </div>
          </div>

                {/* Date Tiles Section */}
                <div className="flex flex-col gap-6">
                  {/* Smart Due Date Tile - Minimal */}
                  <div className="flex items-start gap-3 group">
                    {/* Status Icon */}
                    <Calendar
                      className={cn(
                        "h-5 w-5 mt-0.5 transition-colors shrink-0",
                        getDueDateIconColor(task.dueDate),
                      )}
                    />

                    <div className="flex-1 min-w-0">
                      <p className="text-xs font-medium text-muted-foreground mb-1">
                        Due Date
                      </p>
                      
                      <div className="h-8 flex items-center">
                        {isEditing ? (
                          <>
                            <label htmlFor="task-detail-due-date" className="sr-only">Due Date</label>
                            <Input
                              id="task-detail-due-date"
                              name="dueDate"
                              type="date"
                              value={dueDate}
                              onChange={(e) => setDueDate(e.target.value)}
                              autoComplete="off"
                              aria-label="Due Date"
                              className="bg-transparent border-input px-2 h-8 text-sm w-full font-medium"
                            />
                          </>
                        ) : (
                          <div className="flex items-center gap-2 flex-wrap">
                            <span className="text-sm font-medium text-foreground">
                              {task.dueDate
                                ? format(new Date(task.dueDate), "MMM d, yyyy")
                                : "No date set"}
                            </span>
                            
                            {task.dueDate && (
                              <span
                                className={cn(
                                  "text-[10px] uppercase font-bold px-1.5 py-0.5 rounded-sm tracking-wider",
                                  getDueDateBadgeColor(task.dueDate),
                                )}
                              >
                                {getDueDateLabel(task.dueDate)}
                              </span>
                            )}
                          </div>
                        )}
                      </div>
                    </div>
                  </div>

                  {/* Secondary Details Group */}
                  <div className="space-y-6">
                    {/* Created Date */}
                    <div className="flex items-start gap-3">
                      <Clock className="h-5 w-5 mt-0.5 text-muted-foreground shrink-0" />
                      <div>
                        <p className="text-xs font-medium text-muted-foreground mb-1">
                          Created
                        </p>
                        <p className="text-sm font-medium text-foreground h-8 flex items-center">
                          {format(new Date(task.createdAt), "MMM d, yyyy")}
                        </p>
                      </div>
                    </div>

                    {/* Updated Date */}
                    <div className="flex items-start gap-3">
                      <History className="h-5 w-5 mt-0.5 text-muted-foreground shrink-0" />
                      <div>
                        <p className="text-xs font-medium text-muted-foreground mb-1">
                          Last Updated
                        </p>
                        <p className="text-sm font-medium text-foreground h-8 flex items-center">
                          {format(new Date(task.updatedAt), "MMM d, yyyy")}
                        </p>
                      </div>
                    </div>
                  </div>
                </div>
        </div>
      </div>

      <TaskDeleteDialog
        open={isDeleteModalOpen}
        taskTitle={task.title}
        isDeleting={isDeleting}
        onClose={() => setIsDeleteModalOpen(false)}
        onDelete={handleDelete}
      />
    </div>
  );
}
