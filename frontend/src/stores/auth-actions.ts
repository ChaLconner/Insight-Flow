// ===========================================
// Auth Actions (Separated to avoid circular dependency)
// ===========================================

import { useAuthStore } from "./auth-store";
import { AuthResponse } from "@/types";
import { toast } from "sonner";

// Track initialization state to prevent duplicate calls
// Track initialization state to prevent duplicate calls
// (Moved to auth-store.ts)

// Auth actions that depend on the store but don't create circular imports
export const authActions = {
  // Login function that stores data in localStorage and updates store
  loginSuccess: (response: AuthResponse) => {
    const { login } = useAuthStore.getState();

    // Backend may set HttpOnly cookies, but also returns tokens in body for fallback.
    const user = response.user ?? null;

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

    // Update store (store tokens as well for compatibility)
    login(user);

    // Get display name with fallbacks
    const displayName = user?.name || user?.firstName || user?.username || user?.email || "User";
    
    toast.success(
      `Welcome back, ${displayName}!`,
      {
        description: "You have successfully logged in.",
      },
    );
  },

  // Alternative login method for compatibility
  loginWithResponse: async (response: AuthResponse) => {
    authActions.loginSuccess(response);
  },

  // Logout function
  logout: async () => {
    const { logout, setLoading } = useAuthStore.getState();
    
    // Set loading true to prevent premature redirects by useRequireAuth
    setLoading(true);

    // Attempt server-side logout to clear HttpOnly cookies
    if (typeof window !== "undefined") {
      try {
        const { apiClient, setLoggingOut } = await import("@/lib/api-client");
        
        // First, call the logout API (CSRF token is auto-attached by apiClient)
        // Do NOT set loggingOut flag before this, or the request will be aborted
        await apiClient.post("/auth/logout");
        
        // After successful logout API call, prevent any further API requests
        setLoggingOut(true);
      } catch (_) {
        // ignore errors during logout (e.g. network error, 401, etc.)
        // We still want to clear client state and redirect
        // Set loggingOut to prevent further requests even on error
        const { setLoggingOut } = await import("@/lib/api-client");
        setLoggingOut(true);
      }
    }

    if (typeof window !== "undefined") {
      try {
        const { clearServiceWorkerCache } = await import(
          "@/components/providers/service-worker-registration"
        );
        await clearServiceWorkerCache();
      } catch (_) {
        // Cache clearing is best-effort; logout must continue.
      }
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

// Listen for auth events (only in browser environment)
if (typeof window !== "undefined") {
  window.addEventListener("auth:login", (_event: Event) => {});

  window.addEventListener("auth:logout", () => {});
}
