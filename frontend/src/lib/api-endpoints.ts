// ===========================================
// API Endpoints Mapping - Simplified
// ===========================================

import { apiClient } from './api-client';
import type {
  User,
  Project,
  Task,
  AuthResponse,
  LoginRequest,
  RegisterRequest,
  CreateUserRequest,
  UpdateUserRequest,
  CreateProjectRequest,
  UpdateProjectRequest,
  CreateTaskRequest,
  UpdateTaskRequest,
  Notification,
  PaginatedResponse
} from '@/types';

// ===========================================
// Authentication Endpoints
// ===========================================

export const authApi = {
  // Login
  login: async (credentials: LoginRequest): Promise<AuthResponse> => {
    const { data } = await apiClient.post('/auth/login', credentials);
    return data;
  },

  // Register
  register: async (userData: RegisterRequest): Promise<AuthResponse> => {
    const { data } = await apiClient.post('/auth/register', userData);
    return data;
  },

  // Logout
  logout: async (): Promise<void> => {
    await apiClient.post('/auth/logout');
  },

  // Refresh token
  refreshToken: async (refreshToken: string): Promise<AuthResponse> => {
    const { data } = await apiClient.post('/auth/refresh', {}, {
      headers: {
        'Authorization': `Bearer ${refreshToken}`,
      },
    });
    return data;
  },

  // Get current user profile
  getCurrentUser: async (): Promise<User> => {
    // Log entry and stack to help find duplicate callers
    if (process.env.NODE_ENV === 'development') {
      try {
        console.log('🔍 authApi.getCurrentUser called at', new Date().toISOString());
        // eslint-disable-next-line no-console
        console.log(new Error('authApi.getCurrentUser stack:').stack);
      } catch (e) {
        // ignore
      }
    }

    try {
      const { data } = await apiClient.get('/auth/me');
      return data;
    } catch (err: any) {
      // If cookie-based request fails (401), try Authorization header fallback using stored token
      const status = err?.response?.status;
      if (status === 401) {
        // Check if we have a token before retrying
        const token = typeof window !== 'undefined'
          ? (localStorage.getItem('access_token') || localStorage.getItem('accessToken'))
          : null;
        
        if (!token) {
          console.log('🔍 authApi.getCurrentUser: No token available, not retrying');
          throw err; // No token, don't retry
        }

        try {
          const { API_CONFIG } = await import('@/lib/constants');
          console.log('🔍 authApi.getCurrentUser: Retrying with token from localStorage');
          // Use direct axios call to avoid interceptor side effects
          const axios = (await import('axios')).default;
          const resp = await axios.get(`${API_CONFIG.BASE_URL}/auth/me`, {
            headers: { Authorization: `Bearer ${token}` },
            withCredentials: false, // Bearer token flow, not cookies
          });
          return resp.data;
        } catch (fallbackErr) {
          console.log('🔍 authApi.getCurrentUser: Retry failed');
          // fall through to throw original error
        }
      }
      throw err;
    }
  },

  // Change password
  changePassword: async (currentPassword: string, newPassword: string): Promise<void> => {
    await apiClient.post('/auth/change-password', {
      currentPassword,
      newPassword,
    });
  },

  // Reset password
  resetPassword: async (token: string, newPassword: string): Promise<void> => {
    await apiClient.post('/auth/reset-password', {
      token,
      newPassword,
    });
  },

  // Send reset password email
  forgotPassword: async (email: string): Promise<void> => {
    await apiClient.post('/auth/forgot-password', { email });
  },

  // Verify email
  verifyEmail: async (token: string): Promise<void> => {
    await apiClient.post('/auth/verify-email', { token });
  },

  // Resend verification email
  resendVerification: async (): Promise<void> => {
    await apiClient.post('/auth/resend-verification');
  },
};

// ===========================================
// User Management Endpoints
// ===========================================

export const usersApi = {
  // Get all users (with pagination)
  getUsers: async (params?: {
    page?: number;
    limit?: number;
    search?: string;
    role?: string;
    status?: string;
  }): Promise<PaginatedResponse<User>> => {
    const { data } = await apiClient.get('/users', { params });
    return data;
  },

  // Get user by ID
  getUserById: async (id: string): Promise<User> => {
    const { data } = await apiClient.get(`/users/${id}`);
    return data;
  },

  // Create new user
  createUser: async (userData: CreateUserRequest): Promise<User> => {
    const { data } = await apiClient.post('/users', userData);
    return data;
  },

  // Update user
  updateUser: async (id: string, userData: UpdateUserRequest): Promise<User> => {
    const { data } = await apiClient.put(`/users/${id}`, userData);
    return data;
  },

  // Delete user
  deleteUser: async (id: string): Promise<void> => {
    await apiClient.delete(`/users/${id}`);
  },

  // Deactivate user
  deactivateUser: async (id: string): Promise<void> => {
    await apiClient.post(`/users/${id}/deactivate`);
  },

  // Activate user
  activateUser: async (id: string): Promise<void> => {
    await apiClient.post(`/users/${id}/activate`);
  },

  // Get user profile
  getUserProfile: async (id: string): Promise<any> => {
    const { data } = await apiClient.get(`/users/${id}/profile`);
    return data;
  },

  // Update user profile
  updateUserProfile: async (id: string, profileData: any): Promise<any> => {
    const { data } = await apiClient.put(`/users/${id}/profile`, profileData);
    return data;
  },

  // Upload user avatar
  uploadAvatar: async (id: string, file: File): Promise<{ url: string }> => {
    const formData = new FormData();
    formData.append('avatar', file);
    const { data } = await apiClient.post(`/users/${id}/avatar`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return data;
  },
};

// ===========================================
// Project Management Endpoints
// ===========================================

export const projectsApi = {
  // Get all projects
  getProjects: async (params?: {
    page?: number;
    limit?: number;
    search?: string;
    status?: string;
    ownerId?: string;
  }): Promise<PaginatedResponse<Project>> => {
    const { data } = await apiClient.get('/projects', { params });
    return data;
  },

  // Get project by ID
  getProjectById: async (id: string): Promise<Project> => {
    const { data } = await apiClient.get(`/projects/${id}`);
    return data;
  },

  // Create new project
  createProject: async (projectData: CreateProjectRequest): Promise<Project> => {
    const { data } = await apiClient.post('/projects', projectData);
    return data;
  },

  // Update project
  updateProject: async (id: string, projectData: UpdateProjectRequest): Promise<Project> => {
    const { data } = await apiClient.put(`/projects/${id}`, projectData);
    return data;
  },

  // Delete project
  deleteProject: async (id: string): Promise<void> => {
    await apiClient.delete(`/projects/${id}`);
  },

  // Archive project
  archiveProject: async (id: string): Promise<void> => {
    await apiClient.post(`/projects/${id}/archive`);
  },

  // Restore project
  restoreProject: async (id: string): Promise<void> => {
    await apiClient.post(`/projects/${id}/restore`);
  },

  // Get project members
  getProjectMembers: async (id: string): Promise<any[]> => {
    const { data } = await apiClient.get(`/projects/${id}/members`);
    return data;
  },

  // Add project member
  addProjectMember: async (id: string, userId: string, role: string): Promise<void> => {
    await apiClient.post(`/projects/${id}/members`, { userId, role });
  },

  // Remove project member
  removeProjectMember: async (id: string, userId: string): Promise<void> => {
    await apiClient.delete(`/projects/${id}/members/${userId}`);
  },

  // Update project member role
  updateProjectMemberRole: async (id: string, userId: string, role: string): Promise<void> => {
    await apiClient.put(`/projects/${id}/members/${userId}/role`, { role });
  },

  // Get project statistics
  getProjectStats: async (id: string): Promise<any> => {
    const { data } = await apiClient.get(`/projects/${id}/stats`);
    return data;
  },
};

// ===========================================
// Task Management Endpoints - Simplified
// ===========================================

export const tasksApi = {
  // Get all tasks
  getTasks: async (params?: {
    page?: number;
    limit?: number;
    search?: string;
    status?: string;
    priority?: string;
    projectId?: string;
    assigneeId?: string;
  }): Promise<PaginatedResponse<Task>> => {
    const { data } = await apiClient.get('/tasks', { params });
    return data;
  },

  // Get task by ID - using single endpoint as per backend
  getTaskById: async (id: string): Promise<Task> => {
    const { data } = await apiClient.get(`/tasks/task/${id}`);
    return data;
  },

  // Create new task - using single endpoint as per backend
  createTask: async (taskData: CreateTaskRequest): Promise<Task> => {
    const { data } = await apiClient.post('/tasks/', taskData);
    return data;
  },

  // Create task for project
  createTaskForProject: async (projectId: string, taskData: CreateTaskRequest): Promise<Task> => {
    const { data } = await apiClient.post(`/tasks/projects/${projectId}/tasks`, taskData);
    return data;
  },

  // Update task - using single endpoint as per backend
  updateTask: async (id: string, taskData: UpdateTaskRequest): Promise<Task> => {
    const { data } = await apiClient.put(`/tasks/task/${id}`, taskData);
    return data;
  },

  // Delete task - using single endpoint as per backend
  deleteTask: async (id: string): Promise<void> => {
    await apiClient.delete(`/tasks/task/${id}`);
  },

  // Get task comments
  getTaskComments: async (id: string): Promise<any[]> => {
    const { data } = await apiClient.get(`/tasks/${id}/comments`);
    return data;
  },

  // Add task comment
  addTaskComment: async (id: string, content: string): Promise<any> => {
    const { data } = await apiClient.post(`/tasks/${id}/comments`, { content });
    return data;
  },

  // Update task comment
  updateTaskComment: async (id: string, commentId: string, content: string): Promise<any> => {
    const { data } = await apiClient.put(`/tasks/${id}/comments/${commentId}`, { content });
    return data;
  },

  // Delete task comment
  deleteTaskComment: async (id: string, commentId: string): Promise<void> => {
    await apiClient.delete(`/tasks/${id}/comments/${commentId}`);
  },

  // Get task attachments
  getTaskAttachments: async (id: string): Promise<any[]> => {
    const { data } = await apiClient.get(`/tasks/${id}/attachments`);
    return data;
  },

  // Upload task attachment
  uploadTaskAttachment: async (id: string, file: File): Promise<any> => {
    const formData = new FormData();
    formData.append('file', file);
    const { data } = await apiClient.post(`/tasks/${id}/attachments`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return data;
  },

  // Delete task attachment
  deleteTaskAttachment: async (id: string, attachmentId: string): Promise<void> => {
    await apiClient.delete(`/tasks/${id}/attachments/${attachmentId}`);
  },

  // Get task history
  getTaskHistory: async (id: string): Promise<any[]> => {
    const { data } = await apiClient.get(`/tasks/${id}/history`);
    return data;
  },

  // Assign task - using single endpoint as per backend
  assignTask: async (id: string, assigneeId: string): Promise<Task> => {
    const { data } = await apiClient.put(`/tasks/task/${id}/assign`, { assignee_id: assigneeId });
    return data;
  },

  // Unassign task
  unassignTask: async (id: string): Promise<Task> => {
    const { data } = await apiClient.post(`/tasks/${id}/unassign`);
    return data;
  },

  // Update task status - using single endpoint as per backend
  updateTaskStatus: async (id: string, status: string): Promise<Task> => {
    const { data } = await apiClient.put(`/tasks/task/${id}/status`, { status });
    return data;
  },

  // Get project tasks
  getProjectTasks: async (projectId: string, params?: {
    page?: number;
    limit?: number;
    sortBy?: string;
    sortOrder?: string;
  }): Promise<Task[]> => {
    const { data } = await apiClient.get(`/tasks/projects/${projectId}/tasks`, { params });
    return data;
  },

  // Get my tasks
  getMyTasks: async (params?: {
    page?: number;
    limit?: number;
  }): Promise<Task[]> => {
    const { data } = await apiClient.get('/tasks/my/tasks', { params });
    return data;
  },
};

// ===========================================
// Analytics Endpoints
// ===========================================

export const analyticsApi = {
  // Get project dashboard metrics
  getProjectDashboardMetrics: async (projectId: string): Promise<any> => {
    const { data } = await apiClient.get(`/analytics/projects/${projectId}/dashboard`);
    return data;
  },

  // Get project productivity data
  getProjectProductivity: async (
    projectId: string,
    period: string = '30d',
    groupBy: string = 'week'
  ): Promise<any> => {
    const { data } = await apiClient.get(`/analytics/projects/${projectId}/productivity`, {
      params: { period, groupBy },
    });
    return data;
  },

  // Get project contributions
  getProjectContributions: async (projectId: string): Promise<any> => {
    const { data } = await apiClient.get(`/analytics/projects/${projectId}/contributions`);
    return data;
  },

  // Get project activity
  getProjectActivity: async (
    projectId: string,
    limit: number = 10
  ): Promise<any> => {
    const { data } = await apiClient.get(`/analytics/projects/${projectId}/activity`, {
      params: { limit },
    });
    return data;
  },

  // Get all recent activity
  getAllRecentActivity: async (limit: number = 20): Promise<any> => {
    const { data } = await apiClient.get(`/analytics/activity`, {
      params: { limit },
    });
    return data;
  },

  // Get batch recent activity
  getBatchRecentActivity: async (
    projectIds: string[],
    limit: number = 10
  ): Promise<any> => {
    const { data } = await apiClient.post(`/analytics/activity/batch`, {
      project_ids: projectIds,
      limit,
    });
    return data;
  },

  // Get user analytics
  getUserAnalytics: async (userId: string, period: string = 'month'): Promise<any> => {
    const { data } = await apiClient.get(`/analytics/users/${userId}`, {
      params: { period },
    });
    return data;
  },

  // Get team analytics
  getTeamAnalytics: async (period: string = 'month'): Promise<any> => {
    const { data } = await apiClient.get('/analytics/team', {
      params: { period },
    });
    return data;
  },

  // Get dashboard analytics
  getDashboardAnalytics: async (period: string = 'month'): Promise<any> => {
    const { data } = await apiClient.get('/analytics/dashboard', {
      params: { period },
    });
    return data;
  },

  // Export analytics data
  exportAnalytics: async (
    type: 'project' | 'user' | 'team',
    id: string,
    format: 'csv' | 'pdf' = 'csv'
  ): Promise<Blob> => {
    const response = await apiClient.get(`/analytics/export/${type}/${id}`, {
      params: { format },
      responseType: 'blob',
    });
    return response.data;
  },
};

// ===========================================
// Notification Endpoints
// ===========================================

export const notificationsApi = {
  // Get user notifications
  getNotifications: async (params?: {
    page?: number;
    limit?: number;
    unread?: boolean;
  }): Promise<PaginatedResponse<Notification>> => {
    const { data } = await apiClient.get('/notifications', { params });
    return data;
  },

  // Get unread notifications count
  getUnreadCount: async (): Promise<{ count: number }> => {
    const { data } = await apiClient.get('/notifications/unread-count');
    return data;
  },

  // Mark notification as read
  markAsRead: async (id: string): Promise<void> => {
    await apiClient.patch(`/notifications/${id}/read`);
  },

  // Mark all notifications as read
  markAllAsRead: async (): Promise<void> => {
    await apiClient.patch('/notifications/mark-all-read');
  },

  // Delete notification
  deleteNotification: async (id: string): Promise<void> => {
    await apiClient.delete(`/notifications/${id}`);
  },

  // Update notification preferences
  updatePreferences: async (preferences: any): Promise<void> => {
    await apiClient.put('/notifications/preferences', preferences);
  },
};

// ===========================================
// File Upload Endpoints
// ===========================================

export const filesApi = {
  // Upload file
  uploadFile: async (file: File, folder?: string): Promise<{ url: string; filename: string }> => {
    const formData = new FormData();
    formData.append('file', file);
    if (folder) {
      formData.append('folder', folder);
    }
    
    const { data } = await apiClient.post('/files/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return data;
  },

  // Delete file
  deleteFile: async (url: string): Promise<void> => {
    await apiClient.delete('/files/delete', { data: { url } });
  },

  // Get file info
  getFileInfo: async (url: string): Promise<any> => {
    const { data } = await apiClient.get('/files/info', { params: { url } });
    return data;
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
      totalTasks: number;
      completedTasks: number;
      pendingTasks: number;
      teamMembers: number;
    };
    recentActivities: any[];
    upcomingDeadlines: any[];
    charts: any[];
  }> => {
    const { data } = await apiClient.get('/dashboard/overview');
    return data;
  },

  // Get user's tasks for today
  getTodayTasks: async (): Promise<Task[]> => {
    const { data } = await apiClient.get('/dashboard/today-tasks');
    return data;
  },

  // Get recent projects
  getRecentProjects: async (): Promise<Project[]> => {
    const { data } = await apiClient.get('/dashboard/recent-projects');
    return data;
  },

  // Get team activity
  getTeamActivity: async (): Promise<any[]> => {
    const { data } = await apiClient.get('/dashboard/team-activity');
    return data;
  },
};