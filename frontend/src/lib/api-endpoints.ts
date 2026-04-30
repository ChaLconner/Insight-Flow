// ===========================================
// API Endpoints Mapping - Simplified
// ===========================================

import { apiClient, createDeduplicatedRequest } from "./api-client";
import type {
  User,
  Project,
  Task,
  AuthResponse,
  LoginRequest,
  RegisterRequest,
  UpdateUserRequest,
  CreateProjectRequest,
  UpdateProjectRequest,
  CreateTaskRequest,
  UpdateTaskRequest,
  TaskListResponse,
  Notification,
  RecentActivity,
  InviteUserRequest,
  UserStats,
} from "@/types";
import type {
  AnalyticsResponse,
  TeamWorkloadPaginatedResponse,
  TeamWorkloadParams,
} from "@/app/analytics/types";

// ===========================================
// Authentication Endpoints
// ===========================================

export const authApi = {
  // Login
  login: async (credentials: LoginRequest): Promise<AuthResponse> => {
    const { data } = await apiClient.post("/auth/login", credentials);
    return data;
  },

  // Register
  register: async (userData: RegisterRequest): Promise<AuthResponse> => {
    const { data } = await apiClient.post("/auth/register", userData);
    return data;
  },

  // Logout
  logout: async (): Promise<void> => {
    await apiClient.post("/auth/logout");
  },

  // Refresh token
  refreshToken: async (refreshToken: string): Promise<AuthResponse> => {
    const { data } = await apiClient.post(
      "/auth/refresh",
      {},
      {
        headers: {
          Authorization: `Bearer ${refreshToken}`,
        },
      },
    );
    return data;
  },

  // Get current user profile with deduplication
  getCurrentUser: async (): Promise<User> => {
    const cacheKey = "auth-getCurrentUser";

    return createDeduplicatedRequest(async () => {
      const { data } = await apiClient.get("/auth/me");
      return data;
    }, cacheKey);
  },

  // Change password
  changePassword: async (
    currentPassword: string,
    newPassword: string,
  ): Promise<void> => {
    const response = await apiClient.post("/auth/change-password", {
      currentPassword,
      newPassword,
    });
    return response.data;
  },

  // Forgot password
  forgotPassword: async (email: string): Promise<unknown> => {
    const response = await apiClient.post("/auth/forgot-password", { email });
    return response.data;
  },

  // Reset password
  resetPassword: async (token: string, newPassword: string): Promise<unknown> => {
    const response = await apiClient.post("/auth/reset-password", {
      token,
      new_password: newPassword,
    });
    return response.data;
  },

  // Validate reset token
  validateResetToken: async (token: string): Promise<unknown> => {
    const response = await apiClient.post("/auth/validate-reset-token", {
      token,
    });
    return response.data;
  },
};

// ===========================================
// File Management Endpoints
// ===========================================

export const fileApi = {
  // Upload file
  uploadFile: async (formData: FormData): Promise<unknown> => {
    const { data } = await apiClient.post("/files/upload", formData, {
      headers: { "Content-Type": "multipart/form-data" },
    });
    return data;
  },

  // Delete file
  deleteFile: async (url: string): Promise<void> => {
    await apiClient.delete("/files/delete", { params: { url } });
  },

  // Get file info
  getFileInfo: async (url: string): Promise<unknown> => {
    const { data } = await apiClient.get("/files/info", { params: { url } });
    return data;
  },
};

// ===========================================
// Task Management Endpoints
// ===========================================

export const tasksApi = {
  // Get all tasks for user
  getTasks: async (
    skip = 0,
    limit = 100,
    search?: string,
    status?: string,
  ): Promise<Task[]> => {
    const cacheKey = `tasks-getTasks-${skip}-${limit}-${search}-${status}`;
    return createDeduplicatedRequest(async () => {
      const { data } = await apiClient.get("/tasks/", {
        params: { skip, limit, search, status },
      });
      return data;
    }, cacheKey);
  },

  // Get user's tasks
  getMyTasks: async (
    skip = 0,
    limit = 100,
    search?: string,
    status?: string,
  ): Promise<TaskListResponse | Task[]> => {
    const cacheKey = `tasks-getMyTasks-${skip}-${limit}-${search}-${status}`;
    return createDeduplicatedRequest(async () => {
      const params: Record<string, unknown> = { skip, limit };
      if (search) {
        params.search = search;
      }
      if (status && status !== "all") {
        params.status = status;
      }
      const { data } = await apiClient.get("/tasks/my/tasks", { params });
      return data;
    }, cacheKey);
  },

  // Get task by ID
  getTask: async (taskId: string): Promise<Task> => {
    const cacheKey = `tasks-getTask-${taskId}`;
    return createDeduplicatedRequest(async () => {
      const { data } = await apiClient.get(`/tasks/${taskId}`);
      return data;
    }, cacheKey);
  },

  // Get tasks for a project
  getProjectTasks: async (
    projectId: string,
    skip = 0,
    limit = 100,
    sortBy?: string,
    sortOrder?: string,
    search?: string,
    statusFilter?: string,
  ): Promise<TaskListResponse | Task[]> => {
    const cacheKey = `tasks-getProjectTasks-${projectId}-${skip}-${limit}-${sortBy}-${sortOrder}-${search}-${statusFilter}`;
    return createDeduplicatedRequest(async () => {
      const params: Record<string, unknown> = { skip, limit };
      if (sortBy) {
        params.sort_by = sortBy;
      }
      if (sortOrder) {
        params.sort_order = sortOrder;
      }
      if (search) {
        params.search = search;
      }
      if (statusFilter && statusFilter !== "all") {
        params.status = statusFilter;
      }
      const { data } = await apiClient.get(`/projects/${projectId}/tasks`, {
        params,
      });
      return data;
    }, cacheKey);
  },

  // Create task for a project
  createTask: async (
    projectId: string,
    taskData: CreateTaskRequest,
  ): Promise<Task> => {
    const { data } = await apiClient.post(
      `/projects/${projectId}/tasks`,
      taskData,
    );
    return data;
  },

  // Update task
  updateTask: async (
    taskId: string,
    taskData: UpdateTaskRequest,
  ): Promise<Task> => {
    const { data } = await apiClient.put(`/tasks/${taskId}`, taskData);
    return data;
  },

  // Update project task
  updateProjectTask: async (
    projectId: string,
    taskId: string,
    taskData: UpdateTaskRequest,
  ): Promise<Task> => {
    const { data } = await apiClient.put(
      `/projects/${projectId}/tasks/${taskId}`,
      taskData,
    );
    return data;
  },

  // Delete task
  deleteTask: async (taskId: string): Promise<void> => {
    await apiClient.delete(`/tasks/${taskId}`);
  },

  // Delete project task
  deleteProjectTask: async (
    projectId: string,
    taskId: string,
  ): Promise<void> => {
    await apiClient.delete(`/projects/${projectId}/tasks/${taskId}`);
  },

  // Update task status
  updateTaskStatus: async (taskId: string, status: string): Promise<Task> => {
    const { data } = await apiClient.put(`/tasks/${taskId}/status`, { status });
    return data;
  },

  // Update project task status
  updateProjectTaskStatus: async (
    projectId: string,
    taskId: string,
    status: string,
  ): Promise<Task> => {
    const { data } = await apiClient.put(
      `/projects/${projectId}/tasks/${taskId}/status`,
      { status },
    );
    return data;
  },

  // Assign task
  assignTask: async (taskId: string, assigneeId: string): Promise<Task> => {
    const { data } = await apiClient.put(`/tasks/${taskId}/assign`, {
      assignee_id: assigneeId,
    });
    return data;
  },

  // Assign project task
  assignProjectTask: async (
    projectId: string,
    taskId: string,
    assigneeId: string,
  ): Promise<Task> => {
    const { data } = await apiClient.put(
      `/projects/${projectId}/tasks/${taskId}/assign`,
      { assignee_id: assigneeId },
    );
    return data;
  },
};

// ===========================================
// Project Management Endpoints
// ===========================================

export const projectsApi = {
  // Get all projects with deduplication
  getProjects: async (
    skip = 0,
    limit = 100,
    userProjectsOnly = false,
    search?: string,
    status?: string,
    sortBy?: string,
  ): Promise<Project[]> => {
    const cacheKey = `projects-getProjects-${skip}-${limit}-${userProjectsOnly}-${search}-${status}-${sortBy}`;

    return createDeduplicatedRequest(async () => {
      const params: Record<string, unknown> = {
        skip,
        limit,
        user_projects_only: userProjectsOnly,
      };
      if (search) {
        params.search = search;
      }
      if (status && status !== "all") {
        params.status = status;
      }
      if (sortBy) {
        params.sort_by = sortBy;
      }
      const { data } = await apiClient.get("/projects", {
        params,
      });

      return data;
    }, cacheKey);
  },

  // Get project by ID
  getProject: async (projectId: string): Promise<Project> => {
    const cacheKey = `projects-getProject-${projectId}`;
    return createDeduplicatedRequest(async () => {
      const { data } = await apiClient.get(`/projects/${projectId}`);
      return data;
    }, cacheKey);
  },

  // Create project
  createProject: async (
    projectData: CreateProjectRequest,
  ): Promise<Project> => {
    const { data } = await apiClient.post("/projects", projectData);
    return data;
  },

  // Update project
  updateProject: async (
    projectId: string,
    projectData: UpdateProjectRequest,
  ): Promise<Project> => {
    const { data } = await apiClient.put(`/projects/${projectId}`, projectData);
    return data;
  },

  // Delete project
  deleteProject: async (projectId: string): Promise<void> => {
    await apiClient.delete(`/projects/${projectId}`);
  },

  // Get project members
  getProjectMembers: async (projectId: string): Promise<unknown[]> => {
    const cacheKey = `projects-getProjectMembers-${projectId}`;
    return createDeduplicatedRequest(async () => {
      const { data } = await apiClient.get(`/projects/${projectId}/members`);
      return data;
    }, cacheKey);
  },

  // Add project member
  addProjectMember: async (
    projectId: string,
    memberData: unknown,
  ): Promise<unknown> => {
    const { data } = await apiClient.post(
      `/projects/${projectId}/members`,
      memberData,
    );
    return data;
  },

  // Remove project member
  removeProjectMember: async (
    projectId: string,
    memberUserId: string,
  ): Promise<void> => {
    await apiClient.delete(`/projects/${projectId}/members/${memberUserId}`);
  },

  // Update member role
  updateMemberRole: async (
    projectId: string,
    memberUserId: string,
    role: string,
  ): Promise<unknown> => {
    const { data } = await apiClient.put(
      `/projects/${projectId}/members/${memberUserId}/role`,
      { role },
    );
    return data;
  },
};

// ===========================================
// User Management Endpoints
// ===========================================

export const usersApi = {
  // Get current user profile
  getCurrentUser: async (): Promise<User> => {
    const cacheKey = "users-getCurrentUser";
    return createDeduplicatedRequest(async () => {
      const { data } = await apiClient.get("/users/me");
      return data;
    }, cacheKey);
  },

  // Update current user profile
  updateCurrentUser: async (userData: UpdateUserRequest): Promise<User> => {
    const { data } = await apiClient.put("/users/me", userData);
    return data;
  },

  // Upload user avatar
  uploadAvatar: async (formData: FormData): Promise<User> => {
    const { data } = await apiClient.post("/users/me/avatar", formData, {
      headers: { "Content-Type": "multipart/form-data" },
    });
    return data;
  },

  // Search user by email
  searchUserByEmail: async (email: string): Promise<User> => {
    const cacheKey = `users-searchUserByEmail-${email}`;
    return createDeduplicatedRequest(async () => {
      const { data } = await apiClient.get(`/users/search/${email}`);
      return data;
    }, cacheKey);
  },

  // Search users
  searchUsers: async (
    query: string,
    skip = 0,
    limit = 20,
    role?: string,
    status?: string,
  ): Promise<User[]> => {
    const cacheKey = `users-searchUsers-${query}-${skip}-${limit}-${role}-${status}`;
    return createDeduplicatedRequest(async () => {
      const params: Record<string, unknown> = { q: query, skip, limit };
      if (role && role !== "all") {
        params.role = role;
      }
      if (status && status !== "all") {
        params.status = status;
      }

      const { data } = await apiClient.get("/users/search", { params });
      return data;
    }, cacheKey);
  },

  // Get user settings
  getSettings: async (): Promise<unknown> => {
    const cacheKey = "users-getSettings";
    return createDeduplicatedRequest(async () => {
      const { data } = await apiClient.get("/users/me/settings");
      return data;
    }, cacheKey);
  },

  // Update user settings
  updateSettings: async (settingsData: unknown): Promise<unknown> => {
    const { data } = await apiClient.patch("/users/me/settings", settingsData);
    return data;
  },

  // Invite user
  inviteUser: async (userData: InviteUserRequest): Promise<User> => {
    const { data } = await apiClient.post("/users/invite", userData);
    return data;
  },

  // Get user stats
  getStats: async (): Promise<UserStats> => {
    const cacheKey = "users-getStats";
    return createDeduplicatedRequest(async () => {
      const { data } = await apiClient.get("/users/stats");
      return data;
    }, cacheKey);
  },
};

// ===========================================
// Dashboard Endpoints - Simplified
// ===========================================

export const dashboardApi = {
  // Get dashboard overview
  getOverview: async (): Promise<{
    stats: {
      totalProjects: number;
      totalProjectsChange?: string;
      totalProjectsTrend?: "up" | "down";
      totalTasks: number;
      completedTasks: number;
      pendingTasks: number;
      teamMembers: number;
      inProgressTasks?: number;
      inProgressTasksChange?: string;
      inProgressTasksTrend?: "up" | "down";
      pendingReviewTasks?: number;
      pendingReviewTasksChange?: string;
      pendingReviewTasksTrend?: "up" | "down";
      teamVelocity?: number;
      teamVelocityChange?: string;
      teamVelocityTrend?: "up" | "down";
    };
    recentProjects: Project[];
    recentActivities: RecentActivity[];
    upcomingDeadlines: unknown[];
    charts: unknown[];
  }> => {
    const { data } = await apiClient.get("/dashboard/overview");
    return data;
  },

  // Get user's tasks for today
  getTodayTasks: async (): Promise<Task[]> => {
    const cacheKey = "dashboard-getTodayTasks";
    return createDeduplicatedRequest(async () => {
      const { data } = await apiClient.get("/dashboard/today-tasks");
      return data;
    }, cacheKey);
  },

  // Get recent projects
  getRecentProjects: async (): Promise<Project[]> => {
    const cacheKey = "dashboard-getRecentProjects";
    return createDeduplicatedRequest(async () => {
      const { data } = await apiClient.get("/dashboard/recent-projects");
      return data;
    }, cacheKey);
  },

  // Get team activity
  getTeamActivity: async (): Promise<unknown[]> => {
    const cacheKey = "dashboard-getTeamActivity";
    return createDeduplicatedRequest(async () => {
      const { data } = await apiClient.get("/dashboard/team-activity");
      return data;
    }, cacheKey);
  },
};

// ===========================================
// Analytics Endpoints
// ===========================================

export const analyticsApi = {
  // Get analytics overview
  getAnalytics: async (period: string): Promise<AnalyticsResponse> => {
    const cacheKey = `analytics-getAnalytics-${period}`;
    return createDeduplicatedRequest(async () => {
      const { data } = await apiClient.get("/analytics/overview", {
        params: { period },
      });
      return data;
    }, cacheKey);
  },

  // Get paginated team workload (scalable for 1K-100K users)
  getTeamWorkload: async (
    params: TeamWorkloadParams,
  ): Promise<TeamWorkloadPaginatedResponse> => {
    const { data } = await apiClient.get("/analytics/team-workload", {
      params: {
        page: params.page ?? 1,
        page_size: params.pageSize ?? 10,
        search: params.search ?? undefined,
        sort_by: params.sortBy ?? "tasks",
        sort_order: params.sortOrder ?? "desc",
      },
    });
    return data;
  },
};

// ===========================================
// Notification Endpoints
// ===========================================

export const notificationsApi = {
  // Get all notifications
  getNotifications: async (skip = 0, limit = 50): Promise<Notification[]> => {
    const cacheKey = `notifications-getNotifications-${skip}-${limit}`;
    return createDeduplicatedRequest(async () => {
      const { data } = await apiClient.get("/notifications/", {
        params: { skip, limit },
      });
      return data;
    }, cacheKey);
  },

  // Get unread count
  getUnreadCount: async (): Promise<number> => {
    const cacheKey = "notifications-getUnreadCount";
    return createDeduplicatedRequest(async () => {
      const { data } = await apiClient.get("/notifications/unread-count");
      return data;
    }, cacheKey);
  },

  // Mark as read
  markAsRead: async (notificationId: string): Promise<Notification> => {
    const { data } = await apiClient.put(
      `/notifications/${notificationId}/read`,
    );
    return data;
  },

  // Mark all as read
  markAllAsRead: async (): Promise<Notification[]> => {
    const { data } = await apiClient.put("/notifications/read-all");
    return data;
  },

  // Delete notification
  deleteNotification: async (notificationId: string): Promise<void> => {
    await apiClient.delete(`/notifications/${notificationId}`);
  },
};

// ===========================================
// Payment Endpoints
// ===========================================

export const paymentApi = {
  // Get all plans
  getPlans: async (): Promise<unknown> => {
    const cacheKey = "payment-getPlans";
    return createDeduplicatedRequest(async () => {
      const { data } = await apiClient.get("/payment/plans");
      return data;
    }, cacheKey);
  },

  // Get payment methods
  getPaymentMethods: async (): Promise<unknown> => {
    const { data } = await apiClient.get("/payment/methods");
    return data;
  },

  // Create setup intent
  createSetupIntent: async (): Promise<unknown> => {
    const { data } = await apiClient.post("/payment/setup-intent");
    return data;
  },

  // Set default payment method
  setDefaultPaymentMethod: async (paymentMethodId: string): Promise<void> => {
    await apiClient.put(`/payment/methods/${paymentMethodId}/default`);
  },

  // Delete payment method
  deletePaymentMethod: async (paymentMethodId: string): Promise<void> => {
    await apiClient.delete(`/payment/methods/${paymentMethodId}`);
  },

  // Get subscription
  getSubscription: async (): Promise<unknown> => {
    const { data } = await apiClient.get("/payment/subscription");
    return data;
  },

  // Create or update subscription
  createSubscription: async (data: unknown): Promise<unknown> => {
    const response = await apiClient.post("/payment/subscription", data);
    return response.data;
  },

  // Cancel subscription
  cancelSubscription: async (cancelImmediately = false): Promise<unknown> => {
    const { data } = await apiClient.delete("/payment/subscription", {
      params: { cancel_immediately: cancelImmediately },
    });
    return data;
  },
};

// ===========================================
// Favorites Endpoints
// ===========================================

export interface ToggleFavoriteResponse {
  isFavorite: boolean;
  projectId: string;
  message: string;
}

export interface FavoriteIdsResponse {
  projectIds: string[];
}

export const favoritesApi = {
  // Get favorite project IDs
  getFavoriteIds: async (): Promise<string[]> => {
    const cacheKey = "favorites-getFavoriteIds";
    return createDeduplicatedRequest(async () => {
      const { data } = await apiClient.get<FavoriteIdsResponse>("/favorites");
      return data.projectIds;
    }, cacheKey);
  },

  // Toggle favorite status
  toggleFavorite: async (projectId: string): Promise<ToggleFavoriteResponse> => {
    const { data } = await apiClient.post<ToggleFavoriteResponse>(
      "/favorites/toggle",
      { projectId }
    );
    return data;
  },

  // Add to favorites
  addFavorite: async (projectId: string): Promise<ToggleFavoriteResponse> => {
    const { data } = await apiClient.post<ToggleFavoriteResponse>(
      `/favorites/${projectId}`
    );
    return data;
  },

  // Remove from favorites
  removeFavorite: async (projectId: string): Promise<void> => {
    await apiClient.delete(`/favorites/${projectId}`);
  },
};
