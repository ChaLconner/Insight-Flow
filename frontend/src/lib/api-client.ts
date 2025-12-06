// ===========================================
// API Client Configuration
// ===========================================

import axios, { type AxiosError, type AxiosInstance, type AxiosRequestConfig } from 'axios';
import axiosRetry from 'axios-retry';
import { API_CONFIG, ERROR_MESSAGES } from '@/lib/constants';
import { useAuthStore } from '@/stores/auth-store';
import { toast } from "sonner";

// Request deduplication cache removed for simplicity
// const requestCache = new Map<string, Promise<any>>();

// Create axios instance
// Create axios instance
export const apiClient: AxiosInstance = axios.create({
  baseURL: API_CONFIG.BASE_URL,
  timeout: API_CONFIG.TIMEOUT,
  headers: {
    'Content-Type': 'application/json',
  },
  // Use HttpOnly cookies
  withCredentials: true,
});

// Add retry interceptor
axiosRetry(apiClient, {
  retries: API_CONFIG.RETRY_ATTEMPTS,
  retryDelay: (retryCount) => {
    return API_CONFIG.RETRY_DELAY * Math.pow(2, retryCount); // Exponential backoff
  },
  retryCondition: (error: AxiosError) => {
    // Retry on network errors and 5xx server errors
    if (!error.response) {
      console.log(`🔄 Retrying network error (attempt ${error.config?.['axios-retry']?.retryCount || 0 + 1})`);
      return true;
    }
    if (error.response?.status >= 500) {
      console.log(`🔄 Retrying server error ${error.response.status} (attempt ${error.config?.['axios-retry']?.retryCount || 0 + 1})`);
      return true;
    }
    return false;
  },
  onRetry: (retryCount, error, requestConfig) => {
    console.log(`🔄 Retry attempt ${retryCount} for ${requestConfig.url}`, error.message);
  },
});

// Request interceptor: No longer need to attach tokens manually
apiClient.interceptors.request.use(
  (config) => {
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor for error handling
apiClient.interceptors.response.use(
  (response) => {
    return response;
  },
  async (error: AxiosError) => {
    const originalRequest = error.config as AxiosRequestConfig & { _retry?: boolean };

    // Handle 401 Unauthorized - attempt refresh using cookies
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;

      try {
        // Call refresh endpoint with cookies
        await axios.post(`${API_CONFIG.BASE_URL}/auth/refresh`, {}, {
          withCredentials: true,
        });

        // Retry original request
        return apiClient(originalRequest);
      } catch (refreshError) {
        await clearAuthTokens();
        return Promise.reject(refreshError);
      }
    }

    // Handle other errors
    const errorMessage = getErrorMessage(error);

    return Promise.reject({
      ...error,
      message: errorMessage,
    });
  }
);

// Helper function to clear all authentication tokens
async function clearAuthTokens(): Promise<void> {
  if (typeof window === 'undefined') { return; }

  // Attempt server-side logout to clear HttpOnly cookies
  try {
    toast.error("Session expired", { description: "Please log in again." });
    await axios.post(`${API_CONFIG.BASE_URL}/auth/logout`, {}, { withCredentials: true });
  } catch (e) {
    // ignore
  }

  // Clear store
  useAuthStore.getState().logout();

  // Use Next.js router for navigation instead of window.location
  try {
    const nav = await import('next/navigation');
    nav.redirect('/auth/login');
  } catch (err) {
    // Fallback to window.location if Next.js redirect fails
    window.location.href = '/auth/login';
  }
}

// Helper function to get user-friendly error message
function getErrorMessage(error: AxiosError): string {
  // Enhanced network error handling
  if (!error.response) {
    if (error.code === 'ECONNABORTED') {
      return 'Request timeout. Please check your connection and try again.';
    }
    if (error.code === 'ECONNREFUSED') {
      return 'Cannot connect to server. Please ensure the backend is running.';
    }
    if (error.code === 'ENOTFOUND') {
      return 'Server not found. Please check the API URL.';
    }
    if (error.code === 'ETIMEDOUT') {
      return 'Connection timed out. Please check your connection.';
    }

    // Generic network error with retry info
    const retryCount = error.config?.['axios-retry']?.retryCount || 0;
    if (retryCount > 0) {
      return `Network error after ${retryCount} retry attempts. Please check your connection.`;
    }

    return ERROR_MESSAGES.NETWORK_ERROR;
  }

  const status = error.response.status;
  const data = error.response.data as any;

  switch (status) {
    case 400:
      return data?.message || ERROR_MESSAGES.VALIDATION_ERROR;
    case 401:
      return ERROR_MESSAGES.UNAUTHORIZED;
    case 403:
      return ERROR_MESSAGES.FORBIDDEN;
    case 404:
      return ERROR_MESSAGES.NOT_FOUND;
    case 422:
      return data?.message || ERROR_MESSAGES.VALIDATION_ERROR;
    case 429:
      return ERROR_MESSAGES.RATE_LIMIT_EXCEEDED;
    case 500:
      return ERROR_MESSAGES.SERVER_ERROR;
    default:
      return ERROR_MESSAGES.SERVER_ERROR;
  }
}

// ===========================================
// API Request/Response Types
// ===========================================

export interface ApiError {
  message: string;
  code?: string;
  status?: number;
  details?: any;
}

// Generic API response wrapper
export interface ApiResponse<T = any> {
  success: boolean;
  data?: T;
  message?: string;
  error?: string;
}

// Enhanced type definitions for better type safety
export interface AuthTokens {
  access_token: string;
  refresh_token: string;
  expires_in?: number;
  token_type?: string;
}

export interface RefreshTokenResponse {
  access_token: string;
  refresh_token: string;
  expires_in?: number;
  token_type?: string;
}

// FormData upload helper
export function createFormData(data: Record<string, any>): FormData {
  const formData = new FormData();

  Object.entries(data).forEach(([key, value]) => {
    if (value !== undefined && value != null) {
      if (value instanceof File) {
        formData.append(key, value);
      } else if (Array.isArray(value)) {
        value.forEach((item, index) => {
          if (typeof item === 'object' && item != null) {
            Object.entries(item).forEach(([subKey, subValue]) => {
              formData.append(`${key}[${index}][${subKey}]`, String(subValue));
            });
          } else {
            formData.append(`${key}[${index}]`, String(item));
          }
        });
      } else if (typeof value === 'object') {
        formData.append(key, JSON.stringify(value));
      } else {
        formData.append(key, String(value));
      }
    }
  });

  return formData;
}

// Download file helper with improved error handling
export async function downloadFile(url: string, filename?: string): Promise<void> {
  try {
    const response = await apiClient.get(url, {
      responseType: 'blob',
    });

    const blob = new Blob([response.data]);
    const downloadUrl = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = downloadUrl;
    link.download = filename || 'download';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    window.URL.revokeObjectURL(downloadUrl);
  } catch (error) {
    console.error('Download failed:', error);
    throw error;
  }
}

// Utility function to check if we're in a browser environment
export function isBrowser(): boolean {
  return typeof window !== 'undefined';
}

// Factory function to create custom axios instances
export function createCustomApiClient(baseURL: string, timeout: number = 10000): AxiosInstance {
  return axios.create({
    baseURL,
    timeout,
    headers: {
      'Content-Type': 'application/json',
    },
  });
}

// Enhanced helper function to create deduplicated requests with rate limiting
export function createDeduplicatedRequest<T = any>(
  requestFn: () => Promise<T>,
  cacheKey: string,
  ttl: number = 500
): Promise<T> {
  // Pass-through implementation to remove complexity
  return requestFn();
}

// ===========================================
// Health Check Functions
// ===========================================

// Backend health check with retry
export async function checkBackendHealth(): Promise<boolean> {
  try {
    console.log('🏥 Checking backend health...');
    const response = await apiClient.get('/minimal-test', {
      timeout: 5000 // Shorter timeout for health check
    });
    console.log('✅ Backend health check successful:', response.data);
    return true;
  } catch (error: any) {
    console.error('❌ Backend health check failed:', error.message);
    return false;
  }
}

// Wait for backend to be ready with timeout
export async function waitForBackend(maxAttempts: number = 10, delay: number = 1000): Promise<boolean> {
  for (let attempt = 1; attempt <= maxAttempts; attempt++) {
    console.log(`⏳ Waiting for backend... attempt ${attempt}/${maxAttempts}`);

    const isHealthy = await checkBackendHealth();
    if (isHealthy) {
      console.log('✅ Backend is ready!');
      return true;
    }

    if (attempt < maxAttempts) {
      await new Promise(resolve => setTimeout(resolve, delay));
    }
  }

  console.error('❌ Backend failed to start after maximum attempts');
  return false;
}

// Rate limiting helper for user-initiated actions
export function createRateLimitedRequest<T = any>(
  requestFn: () => Promise<T>,
  cacheKey: string,
  ttl: number = 2000
): Promise<T> {
  // Pass-through implementation to remove complexity
  return requestFn();
}

// ===========================================
// Token Management Helpers
// ===========================================

// Token management helpers removed as we use HttpOnly cookies