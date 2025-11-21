"use client";

import { useState, useEffect } from "react";
import { DashboardLayout } from "@/components/layout/DashboardLayout";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import {
  Search,
  Filter,
  Plus,
  MoreHorizontal,
  Calendar,
 Flag,
  Clock,
  CheckCircle2,
  AlertCircle,
  Play,
  Pause,
  Trash2,
  Edit,
  Eye
} from "lucide-react";
import { TaskStatus, TaskPriority, UserRole } from "@/types";
import type { Task, TaskType, CreateTaskRequest, User } from "@/types";
import { TaskModal } from "@/components/modals/TaskModal";

// API functions for tasks
const fetchTasks = async (): Promise<Task[]> => {
  const token = localStorage.getItem('accessToken');
  if (!token) {
    throw new Error('No access token found');
  }

  const response = await fetch('http://localhost:8000/tasks', {
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    }
  });

  if (!response.ok) {
    if (response.status === 401) {
      localStorage.removeItem('accessToken');
      localStorage.removeItem('refreshToken');
      throw new Error('Authentication required');
    }
    throw new Error(`Failed to fetch tasks: ${response.statusText}`);
  }

  const tasks = await response.json();
  
  // Convert backend response to frontend format
  return tasks.map((task: any) => ({
    id: task.id,
    title: task.title,
    description: task.description,
    status: task.status.toLowerCase() as TaskStatus,
    priority: "medium" as TaskPriority, // Default priority
    type: "feature" as TaskType, // Default type
    projectId: task.project_id,
    project: {
      id: task.project.id,
      name: task.project.name,
      color: "#6366f1", // Default color
      status: "active" as any,
      ownerId: task.project.owner_id,
      owner: {} as any,
      members: [],
      stats: {} as any,
      settings: {} as any,
      createdAt: task.project.created_at,
      updatedAt: task.project.updated_at,
      description: task.project.description || ""
    },
    assigneeId: task.assignee_id,
    assignee: task.assignee ? {
      id: task.assignee.id,
      email: task.assignee.email,
      username: task.assignee.username || task.assignee.email.split('@')[0],
      firstName: task.assignee?.name?.split(' ')[0] || "Unknown",
      lastName: task.assignee?.name?.split(' ')[1] || "User",
      role: "member" as any,
      isActive: task.assignee.is_active,
      emailVerified: true,
      createdAt: task.assignee.created_at,
      updatedAt: task.assignee.updated_at
    } : undefined as User | undefined,
    reporterId: task.created_by,
    reporter: task.creator ? {
      id: task.creator.id,
      email: task.creator.email,
      username: task.creator.username || task.creator.email.split('@')[0],
      firstName: task.creator?.name?.split(' ')[0] || "Unknown",
      lastName: task.creator?.name?.split(' ')[1] || "User",
      role: "member" as any,
      isActive: task.creator.is_active,
      emailVerified: true,
      createdAt: task.creator.created_at,
      updatedAt: task.creator.updated_at
    } : {
      id: "",
      email: "",
      username: "",
      firstName: "",
      lastName: "",
      avatar: undefined,
      role: UserRole.MEMBER,
      isActive: true,
      emailVerified: true,
      lastLoginAt: undefined,
      createdAt: "",
      updatedAt: ""
    },
    tags: [], // Default empty tags
    attachments: [],
    comments: [],
    history: [],
    dueDate: task.due_date,
    estimatedHours: undefined,
    progress: 0,
    dependencies: [],
    customFields: {},
    createdAt: task.created_at,
    updatedAt: task.updated_at
  }));
};

const createTask = async (taskData: any): Promise<Task> => {
  const token = localStorage.getItem('accessToken');
  if (!token) {
    throw new Error('No access token found');
  }

  const response = await fetch('http://localhost:8000/tasks', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      title: taskData.title,
      description: taskData.description,
      project_id: taskData.projectId,
      assignee_id: taskData.assigneeId
    })
  });

  if (!response.ok) {
    throw new Error(`Failed to create task: ${response.statusText}`);
  }

  const task = await response.json();
  return {
    id: task.id,
    title: task.title,
    description: task.description,
    status: task.status.toLowerCase() as TaskStatus,
    priority: "medium" as TaskPriority,
    type: "feature" as TaskType,
    projectId: task.project_id,
    project: {
      id: "unknown",
      name: "Unknown Project",
      color: "#6366f1",
      status: "active" as any,
      ownerId: task.project_id,
      owner: {} as any,
      members: [],
      stats: {} as any,
      settings: {} as any,
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
      description: ""
    },
    assigneeId: task.assignee_id,
    assignee: undefined as User | undefined,
    reporterId: task.created_by,
    reporter: {
      id: "",
      email: "",
      username: "",
      firstName: "",
      lastName: "",
      avatar: undefined,
      role: UserRole.MEMBER,
      isActive: true,
      emailVerified: true,
      lastLoginAt: undefined,
      createdAt: "",
      updatedAt: ""
    },
    tags: [],
    attachments: [],
    comments: [],
    history: [],
    dueDate: task.due_date,
    estimatedHours: undefined,
    progress: 0,
    subtasks: [],
    dependencies: [],
    customFields: {},
    createdAt: task.created_at,
    updatedAt: task.updated_at
  };
};

export default function TasksPage() {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState<TaskStatus | "all">("all");
  const [priorityFilter, setPriorityFilter] = useState<TaskPriority | "all">("all");
  const [isTaskModalOpen, setIsTaskModalOpen] = useState(false);
  const [editingTask, setEditingTask] = useState<Task | null>(null);
  const [modalMode, setModalMode] = useState<"create" | "edit">("create");

  useEffect(() => {
    loadTasks();
  }, []);

  const loadTasks = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await fetchTasks();
      setTasks(data);
    } catch (err) {
      console.error('Error loading tasks:', err);
      setError(err instanceof Error ? err.message : 'Failed to load tasks');
    } finally {
      setLoading(false);
    }
  };

  const filteredTasks = tasks.filter(task => {
    const matchesSearch = task.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
                         task.description?.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesStatus = statusFilter === "all" || task.status === statusFilter;
    const matchesPriority = priorityFilter === "all" || task.priority === priorityFilter;
    return matchesSearch && matchesStatus && matchesPriority;
  });

  const getStatusIcon = (status: TaskStatus) => {
    switch (status) {
      case TaskStatus.TODO:
        return <Clock className="h-4 w-4 text-zinc-400" />;
      case TaskStatus.IN_PROGRESS:
        return <Play className="h-4 w-4 text-blue-400" />;
      case TaskStatus.IN_REVIEW:
        return <Eye className="h-4 w-4 text-amber-400" />;
      case TaskStatus.DONE:
        return <CheckCircle2 className="h-4 w-4 text-emerald-400" />;
      case TaskStatus.CANCELLED:
        return <AlertCircle className="h-4 w-4 text-red-400" />;
    }
  };

  const getStatusBadge = (status: TaskStatus) => {
    const statusConfig = {
      [TaskStatus.TODO]: { label: "To Do", color: "bg-zinc-500/20 text-zinc-400" },
      [TaskStatus.IN_PROGRESS]: { label: "In Progress", color: "bg-blue-500/20 text-blue-400" },
      [TaskStatus.IN_REVIEW]: { label: "In Review", color: "bg-amber-500/20 text-amber-400" },
      [TaskStatus.DONE]: { label: "Done", color: "bg-emerald-500/20 text-emerald-400" },
      [TaskStatus.CANCELLED]: { label: "Cancelled", color: "bg-red-500/20 text-red-400" }
    };
    
    const config = statusConfig[status];
    return (
      <Badge className={config.color}>
        {config.label}
      </Badge>
    );
  };

  const getPriorityBadge = (priority: TaskPriority) => {
    const priorityConfig = {
      [TaskPriority.LOW]: { label: "Low", color: "bg-zinc-500/20 text-zinc-400" },
      [TaskPriority.MEDIUM]: { label: "Medium", color: "bg-amber-500/20 text-amber-400" },
      [TaskPriority.HIGH]: { label: "High", color: "bg-orange-500/20 text-orange-400" },
      [TaskPriority.URGENT]: { label: "Urgent", color: "bg-red-500/20 text-red-400" }
    };
    
    const config = priorityConfig[priority];
    return (
      <Badge className={config.color}>
        {config.label}
      </Badge>
    );
  };

  const isOverdue = (dueDate?: string) => {
    if (!dueDate) {
      return false;
   }
    return new Date(dueDate) < new Date() && !tasks.find(t => t.id === dueDate)?.status;
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString("en-US", {
      month: "short",
      day: "numeric"
    });
  };

  const handleCreateTask = () => {
    setModalMode("create");
    setEditingTask(null);
    setIsTaskModalOpen(true);
  };

  const handleEditTask = (task: Task) => {
    setModalMode("edit");
    setEditingTask(task);
    setIsTaskModalOpen(true);
  };

  const handleTaskSubmit = async (data: CreateTaskRequest) => {
    try {
      if (modalMode === "create") {
        const newTask = await createTask(data);
        setTasks(prev => [...prev, newTask]);
      } else if (editingTask) {
        // TODO: Implement update task API call
        console.log("Update task not implemented yet");
      }
      setIsTaskModalOpen(false);
      setEditingTask(null);
    } catch (error) {
      console.error("Error saving task:", error);
      setError("Failed to save task");
    }
  };

  if (loading) {
    return (
      <DashboardLayout>
        <div className="flex items-center justify-center h-64">
          <div className="text-white">Loading tasks...</div>
        </div>
      </DashboardLayout>
    );
  }

  if (error) {
    return (
      <DashboardLayout>
        <div className="flex flex-col items-center justify-center h-64 space-y-4">
          <div className="text-red-400 text-center">
            <p className="text-lg font-medium">{error}</p>
            <button
              onClick={loadTasks}
              className="mt-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg transition-colors"
            >
              Retry
            </button>
          </div>
        </div>
      </DashboardLayout>
    );
  }

  return (
    <DashboardLayout>
      <div className="space-y-8">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-3xl font-bold tracking-tight text-white">Tasks</h2>
            <p className="mt-1 text-zinc-400">
              Manage and track all your tasks across projects.
            </p>
          </div>
          <Button 
            onClick={handleCreateTask}
            className="bg-indigo-600 hover:bg-indigo-500 text-white"
          >
            <Plus className="h-4 w-4 mr-2" />
            New Task
          </Button>
        </div>

        {/* Search and Filter */}
        <div className="flex flex-col lg:flex-row gap-4">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-zinc-400" />
            <Input
              placeholder="Search tasks..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-10 bg-white/5 border-white/10 text-white placeholder:text-zinc-400"
            />
          </div>
          <div className="flex gap-2">
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value as TaskStatus | "all")}
              className="rounded-lg bg-white/5 border border-white/10 px-3 py-2 text-white text-sm"
            >
              <option value="all">All Status</option>
              <option value={TaskStatus.TODO}>To Do</option>
              <option value={TaskStatus.IN_PROGRESS}>In Progress</option>
              <option value={TaskStatus.IN_REVIEW}>In Review</option>
              <option value={TaskStatus.DONE}>Done</option>
              <option value={TaskStatus.CANCELLED}>Cancelled</option>
            </select>
            <select
              value={priorityFilter}
              onChange={(e) => setPriorityFilter(e.target.value as TaskPriority | "all")}
              className="rounded-lg bg-white/5 border border-white/10 px-3 py-2 text-white text-sm"
            >
              <option value="all">All Priority</option>
              <option value={TaskPriority.URGENT}>Urgent</option>
              <option value={TaskPriority.HIGH}>High</option>
              <option value={TaskPriority.MEDIUM}>Medium</option>
              <option value={TaskPriority.LOW}>Low</option>
            </select>
            <Button variant="outline" size="sm" className="border-white/10 text-white hover:bg-white/5">
              <Filter className="h-4 w-4 mr-2" />
              More
            </Button>
          </div>
        </div>

        {/* Tasks List */}
        <div className="space-y-4">
          {filteredTasks.map((task) => (
            <Card key={task.id} className="border-white/10 bg-white/5 backdrop-blur-sm hover:bg-white/10 transition-colors">
              <CardContent className="p-6">
                <div className="flex items-start gap-4">
                  {/* Status Icon */}
                  <div className="mt-1">
                    {getStatusIcon(task.status)}
                  </div>

                  {/* Task Content */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-start justify-between gap-4">
                      <div className="min-w-0 flex-1">
                        <h3 className="text-lg font-semibold text-white mb-1 truncate">
                          {task.title}
                        </h3>
                        {task.description && (
                          <p className="text-sm text-zinc-300 mb-3 line-clamp-2">
                            {task.description}
                          </p>
                        )}
                        
                        {/* Project Info */}
                        <div className="flex items-center gap-3 mb-3">
                          <div
                            className="h-4 w-4 rounded-sm flex-shrink-0"
                            style={{ backgroundColor: task.project.color }}
                          />
                          <span className="text-sm text-zinc-400 truncate">
                            {task.project.name}
                          </span>
                        </div>

                        {/* Tags */}
                        {task.tags.length > 0 && (
                          <div className="flex flex-wrap gap-2 mb-3">
                            {task.tags.map((tag, index) => (
                              <Badge key={index} variant="secondary" className="bg-white/10 text-zinc-300 text-xs">
                                {tag}
                              </Badge>
                            ))}
                          </div>
                        )}
                      </div>

                      {/* Badges */}
                      <div className="flex flex-col gap-2 items-end">
                        {getStatusBadge(task.status)}
                        {getPriorityBadge(task.priority)}
                      </div>
                    </div>

                    {/* Task Details */}
                    <div className="flex items-center justify-between mt-4">
                      <div className="flex items-center gap-6 text-sm text-zinc-400">
                        {/* Assignee */}
                        {task.assignee && (
                          <div className="flex items-center gap-2">
                            <div className="h-6 w-6 rounded-full bg-zinc-700 border border-white/10 flex items-center justify-center text-xs font-medium text-zinc-300">
                              {(task.assignee?.firstName && typeof task.assignee.firstName === 'string' ? task.assignee.firstName[0] : '')}
                              {(task.assignee?.lastName && typeof task.assignee.lastName === 'string' ? task.assignee.lastName[0] : '')}
                            </div>
                            <span>{task.assignee.firstName || 'Unknown'} {task.assignee.lastName || 'User'}</span>
                          </div>
                        )}

                        {/* Due Date */}
                        {task.dueDate && (
                          <div className="flex items-center gap-1">
                            <Calendar className="h-4 w-4" />
                            <span className={isOverdue(task.dueDate) ? "text-red-400" : ""}>
                              {formatDate(task.dueDate)}
                            </span>
                          </div>
                        )}

                        {/* Estimated Hours */}
                        {task.estimatedHours && (
                          <div className="flex items-center gap-1">
                            <Clock className="h-4 w-4" />
                            <span>{task.estimatedHours}h</span>
                          </div>
                        )}
                      </div>

                      {/* Progress Bar */}
                      {task.status !== TaskStatus.DONE && task.status !== TaskStatus.CANCELLED && (
                        <div className="flex items-center gap-3">
                          <div className="text-sm text-zinc-400 min-w-0">
                            {task.progress}%
                          </div>
                          <div className="h-2 w-20 rounded-full bg-white/10">
                            <div
                              className="h-full rounded-full bg-indigo-500"
                              style={{ width: `${task.progress}%` }}
                            />
                          </div>
                        </div>
                      )}

                      {/* Action Buttons */}
                      <div className="flex items-center gap-1">
                        <Button 
                          variant="ghost" 
                          size="sm" 
                          className="h-8 w-8 p-0 text-zinc-400 hover:text-white"
                          onClick={() => handleEditTask(task)}
                        >
                          <Edit className="h-3 w-3" />
                        </Button>
                        <Button variant="ghost" size="sm" className="h-8 w-8 p-0 text-zinc-400 hover:text-white">
                          <Trash2 className="h-3 w-3" />
                        </Button>
                        <Button variant="ghost" size="sm" className="h-8 w-8 p-0 text-zinc-400 hover:text-white">
                          <MoreHorizontal className="h-3 w-3" />
                        </Button>
                      </div>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>

        {/* Empty State */}
        {filteredTasks.length === 0 && (
          <div className="text-center py-12">
            <div className="mx-auto h-12 w-12 rounded-full bg-white/5 flex items-center justify-center mb-4">
              <Search className="h-6 w-6 text-zinc-400" />
            </div>
            <h3 className="text-lg font-medium text-white mb-2">No tasks found</h3>
            <p className="text-zinc-400 mb-6">
              {searchQuery || statusFilter !== "all" || priorityFilter !== "all"
                ? "Try adjusting your search or filter criteria."
                : "Get started by creating your first task."}
            </p>
            {!searchQuery && statusFilter === "all" && priorityFilter === "all" && (
              <Button className="bg-indigo-600 hover:bg-indigo-500 text-white">
                <Plus className="h-4 w-4 mr-2" />
                Create New Task
              </Button>
            )}
          </div>
        )}

        {/* Task Modal */}
        <TaskModal
          isOpen={isTaskModalOpen}
          onClose={() => setIsTaskModalOpen(false)}
          task={editingTask}
          mode={modalMode}
          onSubmit={handleTaskSubmit}
        />
      </div>
    </DashboardLayout>
  );
}