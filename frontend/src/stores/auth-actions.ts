// ===========================================
// Auth Actions (Separated to avoid circular dependency)
// ===========================================

import { useAuthStore } from "./auth-store";
import { AuthResponse } from "@/types";
import { toast } from "sonner";

const AUTH_LOGOUT_TIMEOUT_MS = 5_000;

// Track initialization state to prevent duplicate calls
// (Moved to auth-store.ts)

// Auth actions that depend on the store but don't create circular imports
export const authActions = {
  // Login function that updates the client user state. Authentication tokens
  // remain in HttpOnly cookies managed by the backend.
  loginSuccess: async (
    response: AuthResponse,
    options: { rememberMe?: boolean } = {},
  ) => {
    const { login } = useAuthStore.getState();

    // Authentication state is established by the backend's HttpOnly cookies,
    // but the user profile is still required to initialize the client store.
    const user = response.user;
    if (!user) {
      throw new Error("Authentication response did not include a user profile");
    }

    await clearClientCaches();

    if (typeof window !== "undefined") {
      // Note: We rely on Zustand persist middleware to handle storage.
      // Manual storage is removed to prevent inconsistencies.
    }

    // Dispatch auth event to notify other parts of the app
    if (typeof window !== "undefined") {
      window.dispatchEvent(
        new CustomEvent("auth:login", {
          detail: { user },
        }),
      );
    }

    // Update user state only; access and refresh tokens remain HttpOnly.
    login(user, { rememberMe: options.rememberMe === true });

    // Get display name with fallbacks
    const displayName = user.name || user.firstName || user.username || user.email || "User";
    
    toast.success(
      `Welcome back, ${displayName}!`,
      {
        description: "You have successfully logged in.",
      },
    );
  },

  // Alternative login method for compatibility
  loginWithResponse: async (
    response: AuthResponse,
    options: { rememberMe?: boolean } = {},
  ) => {
    await authActions.loginSuccess(response, options);
  },

  // Logout function
  logout: async () => {
    const { logout, setLoading } = useAuthStore.getState();
    
    // Set loading true to prevent premature redirects by useRequireAuth
    setLoading(true);
    await clearClientCaches();

    // Attempt server-side logout to clear HttpOnly cookies
    if (typeof window !== "undefined") {
      try {
        const { apiClient, setLoggingOut } = await import("@/lib/api-client");
        
        // First, call the logout API (CSRF token is auto-attached by apiClient)
        // Do NOT set loggingOut flag before this, or the request will be aborted
        // Logout must not leave the user-facing session stuck behind a slow
        // revocation/database request. If the bounded request times out,
        // the catch block still clears client state and redirects the user.
        await apiClient.post("/auth/logout", undefined, {
          timeout: AUTH_LOGOUT_TIMEOUT_MS,
        });
        
        // After successful logout API call, prevent any further API requests
        setLoggingOut(true);
      } catch (error) {
        console.warn("Server-side logout failed; continuing client logout.", error);
        // Ignore errors during logout (e.g. network error, 401, etc.)
        // We still want to clear client state and redirect
        // Set loggingOut to prevent further requests even on error
        const { setLoggingOut } = await import("@/lib/api-client");
        setLoggingOut(true);
      }
    }

    if (typeof window !== "undefined") {
      await clearServiceWorkerCaches();
    }

    // Clear client state (always do this, even if server logout failed)
    logout();

    if (typeof window !== "undefined") {
      window.dispatchEvent(new CustomEvent("auth:logout"));
      toast.info("Logged out", {
        description: "You have been safely logged out.",
      });
    }
  },

  // Alternative logout method for compatibility
  logoutAndRedirect: async (redirectPath: string = "/auth/login?logout=true") => {
    await authActions.logout();
    if (typeof window !== "undefined") {
      window.location.href = redirectPath;
    }
  },

  // Initialize auth function - uses direct store method
  initializeAuth: async () => {
    try {
      const { initializeAuth } = useAuthStore.getState();
      await initializeAuth();
    } catch (error) {
      console.error("Auth initialization failed:", error);
    }
  },
};

async function clearClientCaches(): Promise<void> {
  if (typeof window === "undefined") {
    return;
  }

  try {
    const { clearAuthenticatedCaches } = await import("@/lib/auth-cache");
    await clearAuthenticatedCaches();
  } catch (error) {
    console.warn("Failed to clear authenticated caches.", error);
    // Cache clearing is best-effort; auth transition must continue.
  }

  try {
    const { clearDeduplicatedRequests } = await import("@/lib/api-client");
    clearDeduplicatedRequests();
  } catch (error) {
    console.warn("Failed to clear deduplicated requests.", error);
    // Cache clearing is best-effort; logout must continue.
  }

  try {
    const { clearQueryCache } = await import("@/providers/query-provider");
    clearQueryCache();
  } catch (error) {
    console.warn("Failed to clear the query cache.", error);
    // Cache clearing is best-effort; logout must continue.
  }

  try {
    const { TokenManager } = await import("@/utils/token-manager");
    TokenManager.clearTokens();
  } catch (error) {
    console.warn("Failed to clear legacy auth storage.", error);
    // Cache clearing is best-effort; logout must continue.
  }
}

async function clearServiceWorkerCaches(): Promise<void> {
  try {
    const { clearServiceWorkerCache } = await import(
      "@/components/providers/service-worker-registration"
    );
    await clearServiceWorkerCache();
  } catch (error) {
    console.warn("Failed to clear service-worker caches.", error);
    // Cache clearing is best-effort; logout must continue.
  }
}
