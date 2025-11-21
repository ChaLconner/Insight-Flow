// ===========================================
// API Client Configuration
// ===========================================

import axios, { type AxiosError, type AxiosInstance, type AxiosRequestConfig } from 'axios';
import { API_CONFIG, ERROR_MESSAGES } from '@/lib/constants';

// Create axios instance
export const apiClient: AxiosInstance = axios.create({
  baseURL: API_CONFIG.BASE_URL,
  timeout: API_CONFIG.TIMEOUT,
  headers: {
    'Content-Type': 'application/json',
  },
  // Bearer token flow uses Authorization header; do not rely on cookies
  withCredentials: false,
});

  // Request interceptor: do not add Authorization header when using HttpOnly cookies.
  apiClient.interceptors.request.use(
  (config) => {
    // Ensure we don't send cookies (bearer token flow)
    config.withCredentials = false;
    
    // Attach Authorization header from persisted tokens (localStorage or Zustand persist)
    if (typeof window !== 'undefined') {
      try {
        let token = localStorage.getItem('access_token') || localStorage.getItem('accessToken');

        if (!token) {
          const persisted = localStorage.getItem('insight-flow-auth');
          if (persisted) {
            try {
              const parsed = JSON.parse(persisted);
              const stateCandidate = parsed?.state ?? parsed;
              token = stateCandidate?.accessToken || stateCandidate?.access_token || stateCandidate?.token || null;
            } catch (e) {
              // ignore parse errors
            }
          }
        }

        if (token && config.headers) {
          config.headers.Authorization = `Bearer ${token}`;
        }
      } catch (e) {
        // ignore
      }
    }
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

    // Handle 401 Unauthorized - attempt refresh using refresh token from localStorage
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;

      try {
        // Get refresh token from localStorage or persisted store
        let refreshToken = null;
        if (typeof window !== 'undefined') {
          refreshToken = localStorage.getItem('refresh_token') || localStorage.getItem('refreshToken');
          if (!refreshToken) {
            const persisted = localStorage.getItem('insight-flow-auth');
            if (persisted) {
              try {
                const parsed = JSON.parse(persisted);
                const stateCandidate = parsed?.state ?? parsed;
                refreshToken = stateCandidate?.refreshToken || stateCandidate?.refresh_token || null;
              } catch (e) {}
            }
          }
        }

        if (!refreshToken) {
          await clearAuthTokens();
          return Promise.reject(error);
        }

        // Call refresh endpoint with Authorization: Bearer <refreshToken>
        const response = await axios.post(`${API_CONFIG.BASE_URL}/auth/refresh`, {}, {
          headers: { Authorization: `Bearer ${refreshToken}` },
          withCredentials: false,
        });

        const newAccessToken = response.data?.access_token;
        const newRefreshToken = response.data?.refresh_token;

        if (typeof window !== 'undefined' && newAccessToken && newRefreshToken) {
          localStorage.setItem('access_token', newAccessToken);
          localStorage.setItem('refresh_token', newRefreshToken);
          localStorage.setItem('accessToken', newAccessToken);
          localStorage.setItem('refreshToken', newRefreshToken);
        }

        // Attach new access token to original request
        if (originalRequest.headers) {
          originalRequest.headers.Authorization = `Bearer ${newAccessToken}`;
        }

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
  if (typeof window === 'undefined') return;

  // Attempt server-side logout to clear HttpOnly cookies
  try {
    await axios.post(`${API_CONFIG.BASE_URL}/auth/logout`, {}, { withCredentials: true });
  } catch (e) {
    // ignore
  }

  const tokenKeys = [
    'access_token',
    'refresh_token', 
    'accessToken',
    'refreshToken',
    'user',
    'token',
    'auth_token'
  ];
  
  tokenKeys.forEach(key => {
    localStorage.removeItem(key);
  });

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
  if (!error.response) {
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