// ===========================================
// Constants
// ===========================================

// API Configuration
export const API_CONFIG = {
  BASE_URL: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000',
  WS_URL: process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000',
  TIMEOUT: 30000,
  RETRY_ATTEMPTS: 3,
  RETRY_DELAY: 1000,
} as const;

// Pagination
export const PAGINATION = {
  DEFAULT_PAGE: 1,
  DEFAULT_LIMIT: 20,
  MAX_LIMIT: 100,
} as const;

// File Upload
export const FILE_UPLOAD = {
  MAX_SIZE: 10 * 1024 * 1024, // 10MB
  ALLOWED_TYPES: [
    'image/jpeg',
    'image/png',
    'image/gif',
    'image/webp',
    'application/pdf',
    'text/plain',
    'application/msword',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'text/csv',
  ],
  ALLOWED_EXTENSIONS: ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.pdf', '.txt', '.doc', '.docx', '.csv'],
} as const;

// Theme & Styling
export const THEME = {
  BREAKPOINTS: {
    SM: '640px',
    MD: '768px',
    LG: '1024px',
    XL: '1280px',
    '2XL': '1536px',
  },
  Z_INDEX: {
    TOOLTIP: 1000,
    MODAL: 1100,
    POPOVER: 1200,
    NOTIFICATION: 1300,
    TOAST: 1400,
  },
  ANIMATION_DURATION: {
    FAST: 150,
    NORMAL: 300,
    SLOW: 500,
  },
} as const;

// Status Colors
export const STATUS_COLORS = {
  // Task Status
  TODO: '#64748b',
  IN_PROGRESS: '#3b82f6',
  IN_REVIEW: '#f59e0b',
  DONE: '#22c55e',
  CANCELLED: '#ef4444',

  // Priority
  PRIORITY_LOW: '#22c55e',
  PRIORITY_MEDIUM: '#f59e0b',
  PRIORITY_HIGH: '#f97316',
  PRIORITY_URGENT: '#ef4444',

  // Project Status
  ACTIVE: '#22c55e',
  ARCHIVED: '#64748b',
  SUSPENDED: '#ef4444',

  // Notification Priority
  NOTIFICATION_LOW: '#94a3b8',
  NOTIFICATION_MEDIUM: '#f59e0b',
  NOTIFICATION_HIGH: '#f97316',
  NOTIFICATION_URGENT: '#ef4444',
} as const;

// Project Colors
export const PROJECT_COLORS = [
  '#3b82f6', // Blue
  '#22c55e', // Green
  '#f59e0b', // Amber
  '#ef4444', // Red
  '#8b5cf6', // Purple
  '#06b6d4', // Cyan
  '#f97316', // Orange
  '#84cc16', // Lime
  '#ec4899', // Pink
  '#6b7280', // Gray
] as const;

// Task Priorities
export const TASK_PRIORITIES = [
  { value: 'low', label: 'Low', color: STATUS_COLORS.PRIORITY_LOW, icon: 'ArrowDown' },
  { value: 'medium', label: 'Medium', color: STATUS_COLORS.PRIORITY_MEDIUM, icon: 'Minus' },
  { value: 'high', label: 'High', color: STATUS_COLORS.PRIORITY_HIGH, icon: 'ArrowUp' },
  { value: 'urgent', label: 'Urgent', color: STATUS_COLORS.PRIORITY_URGENT, icon: 'AlertTriangle' },
] as const;

// Task Status
export const TASK_STATUSES = [
  { value: 'todo', label: 'To Do', color: STATUS_COLORS.TODO, icon: 'Circle' },
  { value: 'in_progress', label: 'In Progress', color: STATUS_COLORS.IN_PROGRESS, icon: 'Play' },
  { value: 'in_review', label: 'In Review', color: STATUS_COLORS.IN_REVIEW, icon: 'Eye' },
  { value: 'done', label: 'Done', color: STATUS_COLORS.DONE, icon: 'CheckCircle' },
  { value: 'cancelled', label: 'Cancelled', color: STATUS_COLORS.CANCELLED, icon: 'XCircle' },
] as const;

// Date Formats
export const DATE_FORMATS = {
  SHORT: 'MMM d, yyyy',
  MEDIUM: 'MMM d, yyyy h:mm a',
  LONG: 'MMMM d, yyyy h:mm:ss a',
  TIME: 'h:mm a',
  DATE_TIME: 'MMM d, h:mm a',
} as const;

// Validation Rules
export const VALIDATION = {
  EMAIL_REGEX: /^[^\s@]+@[^\s@]+\.[^\s@]+$/,
  USERNAME_REGEX: /^[a-zA-Z0-9_-]{3,20}$/,
  PASSWORD_MIN_LENGTH: 8,
  USERNAME_MIN_LENGTH: 3,
  USERNAME_MAX_LENGTH: 20,
  PROJECT_NAME_MAX_LENGTH: 100,
  TASK_TITLE_MAX_LENGTH: 200,
  TASK_DESCRIPTION_MAX_LENGTH: 2000,
} as const;

// Navigation
export const NAVIGATION = {
  SIDEBAR_WIDTH: 280,
  HEADER_HEIGHT: 64,
  MOBILE_BREAKPOINT: 768,
} as const;

// Local Storage Keys
export const STORAGE_KEYS = {
  THEME: 'insightflow-theme',
  USER_PREFERENCES: 'insightflow-user-preferences',
  SIDEBAR_COLLAPSED: 'insightflow-sidebar-collapsed',
  RECENT_SEARCHES: 'insightflow-recent-searches',
  DRAFT_FORMS: 'insightflow-draft-forms',
} as const;

// Error Messages
export const ERROR_MESSAGES = {
  NETWORK_ERROR: 'Network error. Please check your connection.',
  UNAUTHORIZED: 'You are not authorized to perform this action.',
  FORBIDDEN: 'Access denied.',
  NOT_FOUND: 'The requested resource was not found.',
  SERVER_ERROR: 'Server error. Please try again later.',
  VALIDATION_ERROR: 'Please check your input and try again.',
  FILE_TOO_LARGE: 'File size exceeds the maximum limit.',
  UNSUPPORTED_FILE_TYPE: 'Unsupported file type.',
  UPLOAD_FAILED: 'File upload failed. Please try again.',
  RATE_LIMIT_EXCEEDED: 'Too many requests. Please wait a moment.',
} as const;

// Success Messages
export const SUCCESS_MESSAGES = {
  LOGIN_SUCCESS: 'Welcome back!',
  LOGOUT_SUCCESS: 'You have been logged out successfully.',
  REGISTER_SUCCESS: 'Account created successfully.',
  PROFILE_UPDATED: 'Profile updated successfully.',
  PASSWORD_CHANGED: 'Password changed successfully.',
  PROJECT_CREATED: 'Project created successfully.',
  PROJECT_UPDATED: 'Project updated successfully.',
  TASK_CREATED: 'Task created successfully.',
  TASK_UPDATED: 'Task updated successfully.',
  FILE_UPLOADED: 'File uploaded successfully.',
  EMAIL_SENT: 'Email sent successfully.',
  SETTINGS_SAVED: 'Settings saved successfully.',
} as const;