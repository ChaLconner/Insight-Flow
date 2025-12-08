// ===========================================
// API Response Types
// ===========================================

export interface ApiResponse<T = any> {
  success: boolean;
  data?: T;
  message?: string;
  error?: string;
  timestamp: string;
}

export interface PaginatedResponse<T = any> extends ApiResponse<T[]> {
  pagination: {
    page: number;
    limit: number;
    total: number;
    totalPages: number;
    hasNext: boolean;
    hasPrevious: boolean;
  };
}

// ===========================================
// User Types
// ===========================================

export interface User {
  id: string;
  email: string;
  username: string;
  name?: string;
  firstName?: string;
  lastName?: string;
  avatar?: string;
  role: UserRole;
  isActive: boolean;
  emailVerified: boolean;
  bio?: string;
  phone?: string;
  location?: string;
  website?: string;
  timezone?: string;
  language?: string;
  theme?: 'light' | 'dark' | 'auto';
  notifications?: {
    email: boolean;
    push: boolean;
    project: boolean;
    task: boolean;
    mention: boolean;
  };
  lastLoginAt?: string;
  createdAt: string;
  updatedAt: string;
}

export enum UserRole {
  ADMIN = 'admin',
  MANAGER = 'manager',
  MEMBER = 'member',
  VIEWER = 'viewer'
}

export interface CreateUserRequest {
  email: string;
  username: string;
  name?: string;
  firstName?: string;
  lastName?: string;
  password: string;
  role: UserRole;
}

export interface InviteUserRequest {
  email: string;
  role: UserRole;
}

export interface UpdateUserRequest {
  email?: string;
  username?: string;
  name?: string;
  firstName?: string;
  lastName?: string;
  avatar?: string;
  role?: UserRole;
  isActive?: boolean;
  bio?: string;
  phone?: string;
  location?: string;
  website?: string;
  timezone?: string;
  language?: string;
  theme?: 'light' | 'dark' | 'auto';
  notifications?: {
    email: boolean;
    push: boolean;
    project: boolean;
    task: boolean;
    mention: boolean;
  };
}

export interface UserProfile {
  id: string;
  userId: string;
  bio?: string;
  phone?: string;
  location?: string;
  timezone?: string;
  language: string;
  theme: 'light' | 'dark' | 'auto';
  notifications: {
    email: boolean;
    push: boolean;
    project: boolean;
    task: boolean;
    mention: boolean;
  };
  createdAt: string;
  updatedAt: string;
}

// ===========================================
// Auth Types
// ===========================================

export interface LoginRequest {
  email: string;
  password: string;
}

export interface RegisterRequest {
  email: string;
  username: string;
  inProgressTasks: number;
  overdueTasks: number;
  teamMembers: number;
  recentActivity: number;
}

export interface AuthResponse {
  user: User;
  accessToken: string;
  refreshToken: string;
  expiresAt: string;
}

export interface TokenPayload {
  userId: string;
  email: string;
  role: UserRole;
  iat: number;
  exp: number;
}

// ===========================================
// Project Types
// ===========================================

export interface Project {
  id: string;
  name: string;
  description?: string;
  color: string;
  status: ProjectStatus;
  ownerId: string;
  owner: User;
  members: ProjectMember[];
  stats: ProjectStats;
  settings: ProjectSettings;
  createdAt: string;
  updatedAt: string;
  taskCount?: number;
  completedTasks?: number;
  memberCount?: number;
  memberSummaries?: ProjectMemberSummary[];
  progress?: number;
}

export enum ProjectStatus {
  ACTIVE = 'active',
  ARCHIVED = 'archived',
  SUSPENDED = 'suspended'
}

export interface ProjectMember {
  id: string;
  userId: string;
  projectId: string;
  role: ProjectRole;
  joinedAt: string;
  user: User;
}

export enum ProjectRole {
  OWNER = 'owner',
  ADMIN = 'admin',
  MEMBER = 'member',
  VIEWER = 'viewer'
}

export interface ProjectMemberSummary {
  id: string;
  userId: string;
  name: string;
  email: string;
  avatar?: string;
  role: ProjectRole;
}

export interface ProjectStats {
  totalTasks: number;
  completedTasks: number;
  inProgressTasks: number;
  overdueTasks: number;
  teamMembers: number;
  recentActivity: number;
}

export interface ProjectSettings {
  allowPublicAccess: boolean;
  requireApproval: boolean;
  defaultTaskVisibility: 'private' | 'team' | 'public';
  notificationSettings: {
    taskAssigned: boolean;
    statusChanged: boolean;
    deadlineApproaching: boolean;
    commentAdded: boolean;
  };
}

export interface CreateProjectRequest {
  name: string;
  description?: string;
  color: string;
  memberIds?: string[];
  settings?: Partial<ProjectSettings>;
}

export interface UpdateProjectRequest {
  name?: string;
  description?: string;
  color?: string;
  status?: ProjectStatus;
  settings?: Partial<ProjectSettings>;
  memberIds?: string[];
}

// ===========================================
// Task Types
// ===========================================

export interface Task {
  id: string;
  title: string;
  description?: string;
  status: TaskStatus;
  priority: TaskPriority;
  type: TaskType;
  projectId: string;
  project: Project;
  assigneeId?: string;
  assignee?: User;
  reporterId: string;
  reporter: User;
  tags: string[];
  attachments: TaskAttachment[];
  comments: TaskComment[];
  history: TaskHistoryEntry[];
  dueDate?: string;
  estimatedHours?: number;
  actualHours?: number;
  progress: number;
  parentId?: string;
  subtasks: Task[];
  dependencies: string[];
  customFields: Record<string, string | number | boolean | null>;
  createdAt: string;
  updatedAt: string;
}

export interface TaskListResponse {
  items: Task[];
  total: number;
  page: number;
  size: number;
  hasMore: boolean;
}

export enum TaskStatus {
  TODO = 'todo',
  IN_PROGRESS = 'in_progress',
  IN_REVIEW = 'in_review',
  DONE = 'done',
  CANCELLED = 'cancelled'
}

export enum TaskPriority {
  LOW = 'low',
  MEDIUM = 'medium',
  HIGH = 'high',
  URGENT = 'urgent'
}

export enum TaskType {
  FEATURE = 'feature',
  BUG = 'bug',
  IMPROVEMENT = 'improvement',
  DOCUMENTATION = 'documentation',
  RESEARCH = 'research',
  OTHER = 'other'
}

export interface TaskAttachment {
  id: string;
  taskId: string;
  fileName: string;
  fileSize: number;
  fileType: string;
  fileUrl: string;
  uploadedBy: string;
  createdAt: string;
}

export interface TaskComment {
  id: string;
  taskId: string;
  userId: string;
  content: string;
  isEdited: boolean;
  mentions: string[];
  createdAt: string;
  updatedAt: string;
  user: User;
}

export interface TaskHistoryEntry {
  id: string;
  taskId: string;
  field: string;
  oldValue: string | number | boolean | null;
  newValue: string | number | boolean | null;
  userId: string;
  createdAt: string;
  user: User;
}

export interface CreateTaskRequest {
  title: string;
  description?: string;
  projectId: string;
  assigneeId?: string;
  priority: TaskPriority;
  type: TaskType;
  dueDate?: string;
  estimatedHours?: number;
  tags?: string[];
  parentId?: string;
  dependencies?: string[];
  customFields?: Record<string, string | number | boolean | null>;
}

export interface UpdateTaskRequest {
  title?: string;
  description?: string;
  status?: TaskStatus;
  priority?: TaskPriority;
  type?: TaskType;
  assigneeId?: string;
  dueDate?: string;
  estimatedHours?: number;
  actualHours?: number;
  progress?: number;
  tags?: string[];
  customFields?: Record<string, string | number | boolean | null>;
}

export interface ProjectAnalytics {
  projectId: string;
  period: AnalyticsPeriod;
  metrics: {
    tasks: TaskMetrics;
    team: TeamMetrics;
    productivity: ProductivityMetrics;
    quality: QualityMetrics;
  };
  trends: AnalyticsTrend[];
  generatedAt: string;
}

export enum AnalyticsPeriod {
  WEEK = 'week',
  MONTH = 'month',
  QUARTER = 'quarter',
  YEAR = 'year'
}

export interface TaskMetrics {
  total: number;
  completed: number;
  inProgress: number;
  overdue: number;
  completionRate: number;
  averageCompletionTime: number; // in hours
  averageTasksPerDay: number;
}

export interface TeamMetrics {
  totalMembers: number;
  activeMembers: number;
  newMembers: number;
  memberUtilization: number; // percentage
  collaborationScore: number; // 0-100
}

export interface ProductivityMetrics {
  velocity: number; // tasks per sprint
  cycleTime: number; // average time from start to completion
  leadTime: number; // average time from creation to completion
  workInProgress: number;
  burndown: BurndownData[];
}

export interface BurndownData {
  date: string;
  planned: number;
  actual: number;
  ideal: number;
}

export interface QualityMetrics {
  defectRate: number;
  reworkRate: number;
  customerSatisfaction: number;
  codeQuality: number;
}

export interface AnalyticsTrend {
  metric: string;
  current: number;
  previous: number;
  change: number;
  changePercentage: number;
  trend: 'up' | 'down' | 'stable';
}

// ===========================================
// Notification Types
// ===========================================

export interface Notification {
  id: string;
  userId: string;
  type: NotificationType;
  title: string;
  message: string;
  data?: Record<string, string | number | boolean | null>;
  read: boolean;
  actionUrl?: string;
  priority: NotificationPriority;
  expiresAt?: string;
  createdAt: string;
  updatedAt: string;
}

export enum NotificationType {
  TASK_ASSIGNED = 'task_assigned',
  TASK_STATUS_CHANGED = 'task_status_changed',
  TASK_DUE_DATE = 'task_due_date',
  PROJECT_INVITATION = 'project_invitation',
  PROJECT_UPDATE = 'project_update',
  MENTION = 'mention',
  COMMENT = 'comment',
  SYSTEM = 'system'
}

export enum NotificationPriority {
  LOW = 'low',
  MEDIUM = 'medium',
  HIGH = 'high',
  URGENT = 'urgent'
}

export interface NotificationPreferences {
  userId: string;
  email: boolean;
  push: boolean;
  inApp: boolean;
  types: Record<NotificationType, boolean>;
  quietHours: {
    enabled: boolean;
    start: string; // HH:mm
    end: string; // HH:mm
    timezone: string;
  };
  createdAt: string;
  updatedAt: string;
}

// ===========================================
// Form Types
// ===========================================

export interface FormError {
  field: string;
  message: string;
  code: string;
}

export interface FormState<T = any> {
  data: T;
  errors: FormError[];
  isSubmitting: boolean;
  isValid: boolean;
  isDirty: boolean;
}

// ===========================================
// UI Types
// ===========================================

export interface BreadcrumbItem {
  label: string;
  href?: string;
  icon?: string;
}

export interface TableColumn<T = any> {
  key: keyof T;
  label: string;
  sortable?: boolean;
  width?: string;
  align?: 'left' | 'center' | 'right';
  render?: (value: T[keyof T], item: T) => React.ReactNode;
}

export interface FilterOption {
  label: string;
  value: string | number;
  count?: number;
}

export interface SortOption {
  field: string;
  direction: 'asc' | 'desc';
}

// ===========================================
// Component Props Types
// ===========================================

export interface BaseComponentProps {
  className?: string;
  children?: React.ReactNode;
  'data-testid'?: string;
}

export interface LoadingState {
  isLoading: boolean;
  error?: string | null;
}

export interface PaginationState {
  page: number;
  limit: number;
  total: number;
  totalPages: number;
}

export interface SearchState {
  query: string;
  filters: Record<string, string | number | boolean | null | string[]>;
  sort?: SortOption;
}

export interface RecentActivity {
  id: string;
  user: {
    name: string;
    id: string;
    avatar?: string;
  };
  action: string;
  target?: string;
  time?: string;
  timestamp?: string;
  project?: string | { name: string; id: string };
}
