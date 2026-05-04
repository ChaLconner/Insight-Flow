// ===========================================
// API Client Configuration
// ===========================================

import axios, {
  type AxiosError,
  type AxiosInstance,
  type AxiosRequestConfig,
} from "axios";
import axiosRetry from "axios-retry";
import { API_CONFIG, ERROR_MESSAGES } from "@/lib/constants";
import { toast } from "sonner";

// ===========================================
// Type Definitions
// ===========================================

// Generic API response wrapper
export interface ApiResponse<T = unknown> {
  success: boolean;
  data?: T;
  message?: string;
  error?: string;
}

// API error interface
export interface ApiError {
  message?: string;
  detail?: string | Record<string, unknown> | Array<unknown>; // FastAPI uses 'detail'
  code?: string;
  status?: number;
  details?: Record<string, unknown>;
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

// Backend health check response
export interface HealthCheckResponse {
  status: "healthy" | "unhealthy";
  message?: string;
}

// ===========================================
// API Client Setup
// ===========================================

// Create axios instance
export const apiClient: AxiosInstance = axios.create({
  baseURL: API_CONFIG.BASE_URL,
  timeout: API_CONFIG.TIMEOUT,
  headers: {
    "Content-Type": "application/json",
  },
  // Use HttpOnly cookies
  withCredentials: true,
});

const IDEMPOTENT_METHODS = new Set(["get", "head", "options", "put", "delete"]);

function getRequestMethod(config?: AxiosRequestConfig): string {
  return config?.method?.toLowerCase() ?? "get";
}

function isAuthRequest(config?: AxiosRequestConfig): boolean {
  const requestUrl = config?.url ?? "";
  return requestUrl.includes("/auth/");
}

export function shouldRetryRequest(error: AxiosError): boolean {
  const method = getRequestMethod(error.config);
  const isIdempotentMethod = IDEMPOTENT_METHODS.has(method);

  if (!isIdempotentMethod || isAuthRequest(error.config)) {
    return false;
  }

  if (!error.response) {
    console.warn(
      `🔄 Retrying network error (attempt ${(error.config?.["axios-retry"]?.retryCount ?? 0) + 1})`,
    );
    return error.code !== "ECONNABORTED";
  }

  if (error.response.status >= 500) {
    console.warn(
      `🔄 Retrying server error ${error.response.status} (attempt ${(error.config?.["axios-retry"]?.retryCount ?? 0) + 1})`,
    );
    return true;
  }

  return false;
}

// Add retry interceptor
axiosRetry(apiClient, {
  retries: API_CONFIG.RETRY_ATTEMPTS,
  retryDelay: (retryCount) => {
    return API_CONFIG.RETRY_DELAY * Math.pow(2, retryCount); // Exponential backoff
  },
  retryCondition: shouldRetryRequest,
  onRetry: (retryCount, error, requestConfig) => {
    console.warn(
      `🔄 Retry attempt ${retryCount} for ${requestConfig.url}`,
      error.message,
    );
  },
});

// Helper to get CSRF token from cookie
function getCSRFToken(): string | null {
  if (!isBrowser()) {
    return null;
  }
  const value = `; ${document.cookie}`;
  const parts = value.split(`; csrf_token=`);
  if (parts.length === 2) {
    return parts.pop()?.split(';').shift() ?? null;
  }
  return null;
}

// Request interceptor: Attach CSRF token and handle logout
apiClient.interceptors.request.use(
  (config) => {
    if (isLoggingOut) {
      // Cancel request if we are logging out
      const controller = new AbortController();
      controller.abort();
      return {
        ...config,
        signal: controller.signal,
      };
    }

    // Attach CSRF token if available (required for state-changing requests)
    const csrfToken = getCSRFToken();
    if (csrfToken) {
      config.headers["X-CSRF-Token"] = csrfToken;
    }

    return config;
  },
  (error) => {
    return Promise.reject(error);
  },
);

// Queue for pending requests while refreshing
let isRefreshing = false;
let failedQueue: Array<{
  resolve: (value: unknown) => void;
  reject: (reason?: unknown) => void;
}> = [];

const processQueue = (error: Error | null, token: unknown = null) => {
  failedQueue.forEach((prom) => {
    if (error) {
      prom.reject(error);
    } else {
      prom.resolve(token);
    }
  });

  failedQueue = [];
};

// Response interceptor for error handling
apiClient.interceptors.response.use(
  (response) => {
    return response;
  },
  async (error: AxiosError<unknown>) => {
    // If we are logging out, suppress all errors to prevent UI flashes/toasts during transition
    if (isLoggingOut) {
      return new Promise(() => {});
    }

    const originalRequest = error.config as AxiosRequestConfig & {
      _retry?: boolean;
    };

    // Handle 401 Unauthorized - attempt refresh using cookies
    // BUT skip refresh for auth endpoints (login, register, etc.) since 401 there
    // means credentials are wrong, not that token needs refresh
    const requestUrl = originalRequest.url ?? '';
    const isAuthEndpoint = requestUrl.includes('/auth/login') || 
                           requestUrl.includes('/auth/register') ||
                           requestUrl.includes('/auth/forgot-password') ||
                           requestUrl.includes('/auth/reset-password') ||
                           requestUrl.includes('/auth/google') ||
                           requestUrl.includes('/auth/github');
    
    if (error.response?.status === 401 && !originalRequest._retry && !isAuthEndpoint) {

      if (isRefreshing) {
        return new Promise((resolve, reject) => {
          failedQueue.push({ resolve, reject });
        })
          .then(() => {
            return apiClient(originalRequest);
          })
          .catch((err) => {
            return Promise.reject(err);
          });
      }

      originalRequest._retry = true;
      isRefreshing = true;

      try {
        // Call refresh endpoint with cookies
        await axios.post(
          `${API_CONFIG.BASE_URL}/auth/refresh`,
          {},
          {
            withCredentials: true,
          },
        );

        processQueue(null);
        isRefreshing = false;

        // Retry original request
        return apiClient(originalRequest);
      } catch (refreshError) {
        processQueue(refreshError as Error);
        isRefreshing = false;

        // Final check: maybe another tab refreshed the token?
        // If we can fetch the user, we are actually still logged in.
        try {
          await axios.get(`${API_CONFIG.BASE_URL}/auth/me`, {
            withCredentials: true,
          });
          // If successful, retry the original request
          return apiClient(originalRequest);
        } catch (_finalError) {
          // Truly unauthorized
          await clearAuthTokens();
          return Promise.reject(refreshError);
        }
      }
    }

    // Handle other errors
    const errorMessage = getErrorMessage(error);

    return Promise.reject({
      ...error,
      message: errorMessage,
    });
  },
);

// ===========================================
// Authentication Helpers
// ===========================================

// State to track if we are currently logging out to prevent loops
let isLoggingOut = false;

export const setLoggingOut = (status: boolean) => {
  isLoggingOut = status;
};

// Callback storage
let logoutCallback: (() => void) | null = null;

export const registerLogoutHandler = (fn: () => void) => {
  logoutCallback = fn;
};

// Helper function to clear all authentication tokens
async function clearAuthTokens(): Promise<void> {
  if (typeof window === "undefined") {
    return;
  }

  setLoggingOut(true);
  clearDeduplicatedRequests();
  await clearClientSideCaches();

  // Always clear the local auth store, even on public/auth pages. This prevents
  // stale persisted users from reviving after cookies were revoked elsewhere.
  if (logoutCallback) {
    logoutCallback();
  }

  // Skip redirect/toast if already on auth pages or landing page to prevent loops.
  const path = window.location.pathname;
  const isOnPublicPage = path.startsWith("/auth/") || path === "/";
  
  if (isOnPublicPage) {
    setLoggingOut(false);
    return;
  }

  // Attempt server-side logout to clear HttpOnly cookies
  try {
    toast.error("Session expired", { description: "Please log in again." });
    await axios.post(
      `${API_CONFIG.BASE_URL}/auth/logout`,
      {},
      { withCredentials: true },
    );
  } catch {
    // ignore
  }

  // Navigate to login page
  window.location.href = "/auth/login";
  // Keep isLoggingOut true until the page unloads
}

// Helper function to get user-friendly error message
export function getErrorMessage(error: AxiosError<unknown>): string {
  // Enhanced network error handling
  if (!error.response) {
    if (error.code === "ECONNABORTED") {
      return "Request timeout. Please check your connection and try again.";
    }
    if (error.code === "ECONNREFUSED") {
      return "Cannot connect to server. Please ensure backend is running.";
    }
    if (error.code === "ENOTFOUND") {
      return "Server not found. Please check API URL.";
    }
    if (error.code === "ETIMEDOUT") {
      return "Connection timed out. Please check your connection.";
    }

    // Generic network error with retry info
    const retryCount = error.config?.["axios-retry"]?.retryCount ?? 0;
    if (retryCount > 0) {
      return `Network error after ${retryCount} retry attempts. Please check your connection.`;
    }

    return ERROR_MESSAGES.NETWORK_ERROR;
  }

  const status = error.response.status;
  const data = error.response.data as ApiError | undefined;

  switch (status) {
    case 400:
      return data?.message ?? (typeof data?.detail === 'string' ? data.detail : JSON.stringify(data?.detail)) ?? ERROR_MESSAGES.VALIDATION_ERROR;
    case 401:
      return ERROR_MESSAGES.UNAUTHORIZED;
    case 403:
      return data?.message ?? (typeof data?.detail === 'string' ? data.detail : ERROR_MESSAGES.FORBIDDEN);
    case 404:
      return data?.message ?? (typeof data?.detail === 'string' ? data.detail : ERROR_MESSAGES.NOT_FOUND);
    case 422:
      return data?.message ?? (typeof data?.detail === 'string' ? data.detail : JSON.stringify(data?.detail)) ?? ERROR_MESSAGES.VALIDATION_ERROR;
    case 429:
      return ERROR_MESSAGES.RATE_LIMIT_EXCEEDED;
    case 500:
      return data?.message ?? (typeof data?.detail === 'string' ? data.detail : ERROR_MESSAGES.SERVER_ERROR);
    default:
      return ERROR_MESSAGES.SERVER_ERROR;
  }
}

// ===========================================
// Utility Functions
// ===========================================

// FormData upload helper
export function createFormData(data: Record<string, FormDataValue>): FormData {
  const formData = new FormData();

  Object.entries(data).forEach(([key, value]) => {
    if (value !== undefined && value != null) {
      if (value instanceof File) {
        formData.append(key, value);
      } else if (Array.isArray(value)) {
        value.forEach((item, index) => {
          if (typeof item === "object" && item != null) {
            Object.entries(item).forEach(([subKey, subValue]) => {
              formData.append(`${key}[${index}][${subKey}]`, String(subValue));
            });
          } else {
            formData.append(`${key}[${index}]`, String(item));
          }
        });
      } else if (typeof value === "object") {
        formData.append(key, JSON.stringify(value));
      } else {
        formData.append(key, String(value));
      }
    }
  });

  return formData;
}

// Type for FormData values
type FormDataValue = string | number | boolean | File | File[] | FormDataValue[] | Record<string, unknown> | null;

// Download file helper with improved error handling
export async function downloadFile(
  url: string,
  filename?: string,
): Promise<void> {
  try {
    const response = await apiClient.get(url, {
      responseType: "blob",
    });

    const blob = new Blob([response.data]);
    const downloadUrl = window.URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = downloadUrl;
    link.download = filename ?? "download";
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    window.URL.revokeObjectURL(downloadUrl);
  } catch (error) {
    console.error("Download failed:", error);
    throw error;
  }
}

// Utility function to check if we're in a browser environment
export function isBrowser(): boolean {
  return typeof window !== "undefined";
}

// Factory function to create custom axios instances
export function createCustomApiClient(
  baseURL: string,
  timeout: number = 10000,
): AxiosInstance {
  return axios.create({
    baseURL,
    timeout,
    headers: {
      "Content-Type": "application/json",
    },
  });
}

// ===========================================
// Request Deduplication
// ===========================================

// In-flight request cache for deduplication
const inFlightRequests = new Map<string, Promise<unknown>>();

/**
 * Creates a deduplicated request that prevents multiple identical concurrent requests.
 * If a request with the same cacheKey is already in-flight, returns that promise instead.
 * @param requestFn - The async function to execute
 * @param cacheKey - Unique key to identify this request
 * @returns Promise resolving to request result
 */
export function createDeduplicatedRequest<T = unknown>(
  requestFn: () => Promise<T>,
  cacheKey: string,
): Promise<T> {
  // Check if there's already an in-flight request with this key
  const existing = inFlightRequests.get(cacheKey);
  if (existing) {
    return existing as Promise<T>;
  }

  // Create new request and store it
  const promise = requestFn()
    .then((result) => {
      // Remove from cache after completion
      inFlightRequests.delete(cacheKey);
      return result;
    })
    .catch((error) => {
      // Remove from cache on error too
      inFlightRequests.delete(cacheKey);
      throw error;
    });

  inFlightRequests.set(cacheKey, promise);
  return promise;
}

export function clearDeduplicatedRequests(): void {
  inFlightRequests.clear();
}

async function clearClientSideCaches(): Promise<void> {
  try {
    const { clearQueryCache } = await import("@/providers/query-provider");
    clearQueryCache();
  } catch {
    // Cache clearing is best-effort; session cleanup must continue.
  }

  try {
    const { clearServiceWorkerCache } = await import(
      "@/components/providers/service-worker-registration"
    );
    await clearServiceWorkerCache();
  } catch {
    // Cache clearing is best-effort; session cleanup must continue.
  }
}

// ===========================================
// Health Check Functions
// ===========================================

// Backend health check with retry
export async function checkBackendHealth(): Promise<boolean> {
  try {
    const _response = await apiClient.get<HealthCheckResponse>("/minimal-test", {
      timeout: 5000, // Shorter timeout for health check
    });

    return true;
  } catch (error) {
    const axiosError = error as AxiosError<unknown>;
    console.error("❌ Backend health check failed:", axiosError.message);
    return false;
  }
}

// Wait for backend to be ready with timeout
export async function waitForBackend(
  maxAttempts: number = 10,
  delay: number = 1000,
): Promise<boolean> {
  for (let attempt = 1; attempt <= maxAttempts; attempt++) {
    const isHealthy = await checkBackendHealth();
    if (isHealthy) {
      return true;
    }

    if (attempt < maxAttempts) {
      await new Promise((resolve) => setTimeout(resolve, delay));
    }
  }

  console.error("❌ Backend failed to start after maximum attempts");
  return false;
}
