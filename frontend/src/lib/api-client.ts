/* eslint-disable @typescript-eslint/no-explicit-any -- preserve backward-compatible client generics */

// ===========================================
// Fetch API Client Configuration (Native Fetch, No Axios)
// ===========================================

import { API_CONFIG, ERROR_MESSAGES } from "@/lib/constants";
import { clearAuthenticatedCaches } from "@/lib/auth-cache";
import { toast } from "sonner";

// ===========================================
// Type Definitions
// ===========================================

export interface ApiResponse<T = unknown> {
  success: boolean;
  data?: T;
  message?: string;
  error?: string;
}

export interface ApiErrorData {
  message?: string;
  detail?: string | Record<string, unknown> | Array<unknown>;
  code?: string;
  status?: number;
  details?: Record<string, unknown>;
}

export class ApiError<T = unknown> extends Error {
  response?: {
    data: T;
    status: number;
    statusText: string;
    headers: Record<string, string>;
  };
  status?: number;
  code?: string;
  config?: { url?: string; method?: string; [key: string]: unknown };
  isAxiosError: boolean;

  constructor(
    message: string,
    response?: { data: T; status: number; statusText: string; headers: Record<string, string> },
    config?: { url?: string; method?: string; [key: string]: unknown },
    code?: string
  ) {
    super(message);
    this.name = "ApiError";
    this.response = response;
    this.status = response?.status;
    this.config = config;
    this.code = code;
    this.isAxiosError = true;
  }
}

// Type alias for backward compatibility
export type AxiosError<T = unknown> = ApiError<T>;

export function isAxiosError(error: unknown): error is ApiError<any> {
  return Boolean(
    error &&
      typeof error === "object" &&
      ("isAxiosError" in error || "response" in error || (error as Error).name === "ApiError")
  );
}

export interface AuthTokens {
  access_token: string;
  refresh_token: string;
  expires_in?: number;
  token_type?: string;
}

export type RefreshTokenResponse = AuthTokens;

export interface HealthCheckResponse {
  status: "healthy" | "unhealthy";
  message?: string;
}

export interface FetchRequestConfig extends RequestInit {
  baseURL?: string;
  params?: Record<string, unknown>;
  timeout?: number;
  responseType?: "json" | "blob" | "text";
  withCredentials?: boolean;
  /** Internal auth-state controls; never forwarded to fetch. */
  skipAuthRefresh?: boolean;
  skipLogoutGuard?: boolean;
  authRetry?: boolean;
}

export interface AxiosLikeResponse<T = unknown> {
  data: T;
  status?: number;
  statusText?: string;
  headers?: Record<string, string>;
  config?: FetchRequestConfig;
}

// ===========================================
// Fetch Client Implementation
// ===========================================

let isLoggingOut = false;

export const setLoggingOut = (status: boolean) => {
  isLoggingOut = status;
};

let logoutCallback: (() => void) | null = null;

export const registerLogoutHandler = (fn: () => void) => {
  logoutCallback = fn;
};

function getCSRFToken(): string | null {
  if (!isBrowser()) {
    return null;
  }
  const value = `; ${document.cookie}`;
  const parts = value.split(`; csrf_token=`);
  if (parts.length === 2) {
    return parts.pop()?.split(";").shift() ?? null;
  }
  return null;
}

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

async function executeFetch<T = any>(
  endpoint: string,
  config: FetchRequestConfig = {}
): Promise<AxiosLikeResponse<T>> {
  if (isLoggingOut && !config.skipLogoutGuard) {
    return new Promise(() => {});
  }

  const baseURL = config.baseURL ?? API_CONFIG.BASE_URL;
  let url = endpoint.startsWith("http") ? endpoint : `${baseURL}${endpoint}`;

  if (config.params) {
    const searchParams = new URLSearchParams();
    Object.entries(config.params).forEach(([key, val]) => {
      if (val != null) {
        searchParams.append(key, String(val));
      }
    });
    const queryString = searchParams.toString();
    if (queryString) {
      url += (url.includes("?") ? "&" : "?") + queryString;
    }
  }

  const headers: Record<string, string> = {
    ...(config.body instanceof FormData ? {} : { "Content-Type": "application/json" }),
    ...(config.headers as Record<string, string>),
  };

  const csrfToken = getCSRFToken();
  if (csrfToken) {
    headers["X-CSRF-Token"] = csrfToken;
  }

  const timeoutMs = config.timeout ?? API_CONFIG.TIMEOUT;
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

  const requestConfig = { ...config };
  delete requestConfig.skipAuthRefresh;
  delete requestConfig.skipLogoutGuard;
  delete requestConfig.authRetry;

  const fetchOptions: RequestInit = {
    ...requestConfig,
    headers,
    signal: controller.signal,
    credentials: config.withCredentials !== false ? "include" : "same-origin",
  };

  try {
    const res = await fetch(url, fetchOptions);
    clearTimeout(timeoutId);

    const resHeaders: Record<string, string> = {};
    res.headers.forEach((value, key) => {
      resHeaders[key] = value;
    });

    let data: any;
    if (config.responseType === "blob") {
      data = await res.blob();
    } else if (config.responseType === "text") {
      data = await res.text();
    } else {
      const text = await res.text();
      try {
        data = text ? JSON.parse(text) : {};
      } catch {
        data = text;
      }
    }

    if (!res.ok) {
      const errorObj = new ApiError(
        typeof data?.detail === "string" ? data.detail : data?.message ?? `HTTP error ${res.status}`,
        {
          data,
          status: res.status,
          statusText: res.statusText,
          headers: resHeaders,
        },
        { url, method: config.method }
      );

      // Handle 401 Unauthorized token refresh
      const isAuthEndpoint =
        endpoint.includes("/auth/login") ||
        endpoint.includes("/auth/register") ||
        endpoint.includes("/auth/forgot-password") ||
        endpoint.includes("/auth/reset-password") ||
        endpoint.includes("/auth/google") ||
        endpoint.includes("/auth/github") ||
        endpoint.includes("/auth/refresh") ||
        endpoint.includes("/auth/logout") ||
        endpoint.includes("/auth/me");

      if (res.status === 401 && !config.skipAuthRefresh && !config.authRetry && !isAuthEndpoint) {
        if (isRefreshing) {
          return new Promise((resolve, reject) => {
            failedQueue.push({ resolve, reject });
          }).then(() => executeFetch<T>(endpoint, { ...config, authRetry: true }));
        }

        isRefreshing = true;
        try {
          await executeFetch("/auth/refresh", {
            method: "POST",
            skipAuthRefresh: true,
            skipLogoutGuard: true,
          });
          processQueue(null);
          return executeFetch<T>(endpoint, { ...config, authRetry: true });
        } catch (refreshErr) {
          try {
            await executeFetch("/auth/me", {
              method: "GET",
              skipAuthRefresh: true,
              skipLogoutGuard: true,
            });
            processQueue(null);
            return executeFetch<T>(endpoint, { ...config, authRetry: true });
          } catch {
            processQueue(refreshErr as Error);
            await clearAuthTokens();
            throw refreshErr;
          }
        } finally {
          isRefreshing = false;
        }
      }

      throw errorObj;
    }

    return {
      data,
      status: res.status,
      statusText: res.statusText,
      headers: resHeaders,
      config,
    };
  } catch (err: any) {
    clearTimeout(timeoutId);
    if (err instanceof ApiError) {
      throw err;
    }
    const isTimeout = err.name === "AbortError";
    throw new ApiError(
      isTimeout ? "Request timeout. Please try again." : err.message ?? ERROR_MESSAGES.NETWORK_ERROR,
      undefined,
      { url, method: config.method },
      isTimeout ? "ECONNABORTED" : undefined
    );
  }
}

export const apiClient = {
  get: <T = any>(url: string, config?: FetchRequestConfig) =>
    executeFetch<T>(url, { ...config, method: "GET" }),
  post: <T = any>(url: string, data?: any, config?: FetchRequestConfig) =>
    executeFetch<T>(url, {
      ...config,
      method: "POST",
      body: data instanceof FormData ? data : data !== undefined ? JSON.stringify(data) : undefined,
    }),
  put: <T = any>(url: string, data?: any, config?: FetchRequestConfig) =>
    executeFetch<T>(url, {
      ...config,
      method: "PUT",
      body: data instanceof FormData ? data : data !== undefined ? JSON.stringify(data) : undefined,
    }),
  patch: <T = any>(url: string, data?: any, config?: FetchRequestConfig) =>
    executeFetch<T>(url, {
      ...config,
      method: "PATCH",
      body: data instanceof FormData ? data : data !== undefined ? JSON.stringify(data) : undefined,
    }),
  delete: <T = any>(url: string, config?: FetchRequestConfig) =>
    executeFetch<T>(url, { ...config, method: "DELETE" }),
  create: (opts: FetchRequestConfig) => ({
    get: <T = any>(url: string, config?: FetchRequestConfig) =>
      executeFetch<T>(url, { ...opts, ...config, method: "GET" }),
    post: <T = any>(url: string, data?: any, config?: FetchRequestConfig) =>
      executeFetch<T>(url, {
        ...opts,
        ...config,
        method: "POST",
        body: data instanceof FormData ? data : data !== undefined ? JSON.stringify(data) : undefined,
      }),
  }),
};

async function clearAuthTokens(): Promise<void> {
  if (!isBrowser()) {
    return;
  }

  setLoggingOut(true);
  clearDeduplicatedRequests();
  await clearClientSideCaches();

  if (logoutCallback) {
    logoutCallback();
  }

  const path = window.location.pathname;
  const isOnPublicPage = path.startsWith("/auth/") || path === "/";

  if (isOnPublicPage) {
    setLoggingOut(false);
    return;
  }

  try {
    toast.error("Session expired", { description: "Please log in again." });
    await apiClient.post(
      "/auth/logout",
      undefined,
      { skipAuthRefresh: true, skipLogoutGuard: true }
    );
  } catch {
    // ignore
  } finally {
    setLoggingOut(false);
  }

  window.location.href = "/auth/login";
}

export function getAxiosErrorMessage(error: ApiError | any): string {
  if (!error.response) {
    if (error.code === "ECONNABORTED") {
      return "Request timeout. Please check your connection and try again.";
    }
    return ERROR_MESSAGES.NETWORK_ERROR;
  }

  const status = error.response.status;
  const data = error.response.data as ApiErrorData | undefined;

  switch (status) {
    case 400:
      return (
        data?.message ??
        (typeof data?.detail === "string" ? data.detail : JSON.stringify(data?.detail)) ??
        ERROR_MESSAGES.VALIDATION_ERROR
      );
    case 401:
      return ERROR_MESSAGES.UNAUTHORIZED;
    case 403:
      return data?.message ?? (typeof data?.detail === "string" ? data.detail : ERROR_MESSAGES.FORBIDDEN);
    case 404:
      return data?.message ?? (typeof data?.detail === "string" ? data.detail : ERROR_MESSAGES.NOT_FOUND);
    case 422:
      return (
        data?.message ??
        (typeof data?.detail === "string" ? data.detail : JSON.stringify(data?.detail)) ??
        ERROR_MESSAGES.VALIDATION_ERROR
      );
    case 429:
      return ERROR_MESSAGES.RATE_LIMIT_EXCEEDED;
    case 500:
      return data?.message ?? (typeof data?.detail === "string" ? data.detail : ERROR_MESSAGES.SERVER_ERROR);
    default:
      return ERROR_MESSAGES.SERVER_ERROR;
  }
}

export function createFormData(data: Record<string, any>): FormData {
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

export async function downloadFile(url: string, filename?: string): Promise<void> {
  try {
    const response = await apiClient.get(url, { responseType: "blob" });
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

export function isBrowser(): boolean {
  return typeof window !== "undefined";
}

export function createCustomApiClient(baseURL: string, timeout: number = 10000) {
  return apiClient.create({ baseURL, timeout });
}

const inFlightRequests = new Map<string, Promise<unknown>>();

export function createDeduplicatedRequest<T = unknown>(
  requestFn: () => Promise<T>,
  cacheKey: string
): Promise<T> {
  const existing = inFlightRequests.get(cacheKey);
  if (existing) {
    return existing as Promise<T>;
  }

  const promise = requestFn()
    .then((result) => {
      inFlightRequests.delete(cacheKey);
      return result;
    })
    .catch((error) => {
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
  await clearAuthenticatedCaches();

  try {
    const { clearQueryCache } = await import("@/providers/query-provider");
    clearQueryCache();
  } catch {
    // ignore
  }

  try {
    const { clearServiceWorkerCache } = await import(
      "@/components/providers/service-worker-registration"
    );
    await clearServiceWorkerCache();
  } catch {
    // ignore
  }
}

export async function checkBackendHealth(): Promise<boolean> {
  try {
    await apiClient.get<HealthCheckResponse>("/minimal-test", { timeout: 5000 });
    return true;
  } catch {
    return false;
  }
}

export async function waitForBackend(
  maxAttempts: number = 10,
  delay: number = 1000
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
  return false;
}
