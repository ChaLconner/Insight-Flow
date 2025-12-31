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
        const { setLoggingOut } = await import("@/lib/api-client");
        const { API_CONFIG } = await import("@/lib/constants");
        
        setLoggingOut(true);

        await fetch(`${API_CONFIG.BASE_URL}/auth/logout`, {
          method: "POST",
          credentials: "include",
        });
      } catch (_) {
        // ignore errors during logout (e.g. network error)
      }
    }

    // Clear client state
    logout();

    if (typeof window !== "undefined") {
      window.dispatchEvent(new CustomEvent("auth:logout"));
      toast.info("Logged out", {
        description: "You have been safely logged out.",
      });
    }
  },

  // Alternative logout method for compatibility
  logoutAndRedirect: async (redirectPath: string = "/auth/login") => {
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
