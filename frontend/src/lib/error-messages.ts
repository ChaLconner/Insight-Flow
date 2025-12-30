/**
 * Centralized error messages for Insight-Flow frontend.
 * User-friendly, consistent error messages in English.
 */

export const ErrorMessages = {
  // ===================================
  // Authentication Errors
  // ===================================
  AUTH: {
    INVALID_CREDENTIALS:
      "Invalid email or password. Please check your credentials and try again.",
    SESSION_EXPIRED: "Your session has expired. Please log in again.",
    TOKEN_INVALID: "Invalid authentication token. Please log in again.",
    ACCOUNT_INACTIVE:
      "Your account has been deactivated. Please contact support.",
    ACCOUNT_NOT_VERIFIED:
      "Please verify your email address before logging in.",
    PASSWORD_MISMATCH: "The passwords you entered do not match.",
    PASSWORD_TOO_WEAK:
      "Password must be at least 8 characters with a mix of letters and numbers.",
    EMAIL_ALREADY_EXISTS: "An account with this email already exists.",
    EMAIL_NOT_FOUND: "No account found with this email address.",
    LOGIN_FAILED: "Login failed. Please try again.",
    LOGOUT_FAILED: "Failed to log out. Please try again.",
  },

  // ===================================
  // Permission Errors
  // ===================================
  PERMISSION: {
    DENIED: "You don't have permission to perform this action.",
    NOT_PROJECT_MEMBER: "You are not a member of this project.",
    NOT_PROJECT_OWNER: "Only the project owner can perform this action.",
    INSUFFICIENT_ROLE:
      "Your role does not have sufficient permissions for this action.",
    ACCESS_DENIED: "You don't have access to this resource.",
  },

  // ===================================
  // Resource Not Found Errors
  // ===================================
  NOT_FOUND: {
    USER: "User not found.",
    PROJECT:
      "The project you're looking for doesn't exist or has been deleted.",
    TASK: "The task you're looking for doesn't exist or has been deleted.",
    FILE: "The file you're looking for doesn't exist or has been deleted.",
    PAGE: "The page you're looking for doesn't exist.",
    RESOURCE: "The requested resource was not found.",
  },

  // ===================================
  // Validation Errors
  // ===================================
  VALIDATION: {
    REQUIRED: "This field is required.",
    INVALID_FORMAT: "The format of this field is invalid.",
    INVALID_EMAIL: "Please enter a valid email address.",
    TOO_SHORT: "This value is too short.",
    TOO_LONG: "This value is too long.",
    INVALID_DATE: "Please enter a valid date.",
    DATE_IN_PAST: "The date cannot be in the past.",
    FORM_INVALID: "Please fix the errors in the form before submitting.",
  },

  // ===================================
  // Network Errors
  // ===================================
  NETWORK: {
    CONNECTION_FAILED: "Unable to connect to the server. Please check your internet connection.",
    TIMEOUT: "The request timed out. Please try again.",
    SERVER_ERROR: "An unexpected server error occurred. Please try again later.",
    SERVICE_UNAVAILABLE: "The service is temporarily unavailable. Please try again later.",
  },

  // ===================================
  // Rate Limiting
  // ===================================
  RATE_LIMIT: {
    EXCEEDED: "Too many requests. Please wait a moment and try again.",
    LOGIN: "Too many login attempts. Please wait a few minutes before trying again.",
  },

  // ===================================
  // File Errors
  // ===================================
  FILE: {
    TOO_LARGE: "The file is too large. Maximum file size is {maxSize}MB.",
    TYPE_NOT_ALLOWED: "This file type is not allowed.",
    UPLOAD_FAILED: "File upload failed. Please try again.",
    DELETE_FAILED: "Failed to delete the file. Please try again.",
  },

  // ===================================
  // Payment/Subscription Errors
  // ===================================
  PAYMENT: {
    FAILED:
      "Payment processing failed. Please check your payment details and try again.",
    CARD_DECLINED:
      "Your card was declined. Please try a different payment method.",
    CARD_EXPIRED: "Your card has expired. Please update your payment method.",
    SUBSCRIPTION_REQUIRED:
      "This feature requires a subscription. Please upgrade your plan.",
    LIMIT_REACHED:
      "You've reached the limit for your current plan. Please upgrade to continue.",
  },

  // ===================================
  // Usage Limits
  // ===================================
  LIMITS: {
    PROJECTS: "You've reached the maximum number of projects for your plan.",
    MEMBERS: "You've reached the maximum number of team members for your plan.",
    STORAGE: "You've reached the storage limit for your plan.",
    TASKS: "You've reached the maximum number of tasks for this project.",
  },

  // ===================================
  // Generic Errors
  // ===================================
  GENERIC: {
    UNKNOWN: "An unexpected error occurred. Please try again.",
    OPERATION_FAILED: "The operation failed. Please try again.",
    LOADING_FAILED: "Failed to load data. Please refresh the page.",
    SAVE_FAILED: "Failed to save changes. Please try again.",
    DELETE_FAILED: "Failed to delete. Please try again.",
  },
} as const;

/**
 * Error codes that can be returned from the API.
 * Used for mapping server errors to user-friendly messages.
 */
export const ErrorCodes = {
  // Authentication
  AUTH_INVALID_CREDENTIALS: "AUTH_001",
  AUTH_SESSION_EXPIRED: "AUTH_002",
  AUTH_TOKEN_INVALID: "AUTH_003",
  AUTH_ACCOUNT_INACTIVE: "AUTH_004",

  // Authorization
  PERMISSION_DENIED: "PERM_001",
  NOT_PROJECT_MEMBER: "PERM_002",

  // Not Found
  USER_NOT_FOUND: "NOT_FOUND_001",
  PROJECT_NOT_FOUND: "NOT_FOUND_002",
  TASK_NOT_FOUND: "NOT_FOUND_003",

  // Validation
  VALIDATION_ERROR: "VALID_001",

  // Rate Limiting
  RATE_LIMITED: "RATE_001",

  // Payment
  PAYMENT_FAILED: "PAY_001",
  SUBSCRIPTION_REQUIRED: "PAY_002",

  // Server
  INTERNAL_ERROR: "SYS_001",
  SERVICE_UNAVAILABLE: "SYS_002",
} as const;

/**
 * Map API error codes to user-friendly messages.
 */
export function getErrorMessage(
  code: string | undefined,
  defaultMessage?: string,
): string {
  switch (code) {
    case ErrorCodes.AUTH_INVALID_CREDENTIALS:
      return ErrorMessages.AUTH.INVALID_CREDENTIALS;
    case ErrorCodes.AUTH_SESSION_EXPIRED:
      return ErrorMessages.AUTH.SESSION_EXPIRED;
    case ErrorCodes.AUTH_TOKEN_INVALID:
      return ErrorMessages.AUTH.TOKEN_INVALID;
    case ErrorCodes.AUTH_ACCOUNT_INACTIVE:
      return ErrorMessages.AUTH.ACCOUNT_INACTIVE;
    case ErrorCodes.PERMISSION_DENIED:
      return ErrorMessages.PERMISSION.DENIED;
    case ErrorCodes.NOT_PROJECT_MEMBER:
      return ErrorMessages.PERMISSION.NOT_PROJECT_MEMBER;
    case ErrorCodes.USER_NOT_FOUND:
      return ErrorMessages.NOT_FOUND.USER;
    case ErrorCodes.PROJECT_NOT_FOUND:
      return ErrorMessages.NOT_FOUND.PROJECT;
    case ErrorCodes.TASK_NOT_FOUND:
      return ErrorMessages.NOT_FOUND.TASK;
    case ErrorCodes.RATE_LIMITED:
      return ErrorMessages.RATE_LIMIT.EXCEEDED;
    case ErrorCodes.PAYMENT_FAILED:
      return ErrorMessages.PAYMENT.FAILED;
    case ErrorCodes.SUBSCRIPTION_REQUIRED:
      return ErrorMessages.PAYMENT.SUBSCRIPTION_REQUIRED;
    case ErrorCodes.INTERNAL_ERROR:
    case ErrorCodes.SERVICE_UNAVAILABLE:
      return ErrorMessages.NETWORK.SERVER_ERROR;
    default:
      return defaultMessage ?? ErrorMessages.GENERIC.UNKNOWN;
  }
}

/**
 * Format an error message template with dynamic values.
 */
export function formatError(
  template: string,
  params: Record<string, string | number>,
): string {
  let result = template;
  for (const [key, value] of Object.entries(params)) {
    result = result.replace(`{${key}}`, String(value));
  }
  return result;
}
