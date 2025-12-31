// ===========================================
// Zustand Auth Store
// ===========================================

import { create } from "zustand";
import { persist } from "zustand/middleware";
import { User, UpdateUserRequest } from "@/types";

interface AuthState {
  // State
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  lastActivity: number;
  isInitialized: boolean;

  // Actions
  setUser: (user: User | null) => void;
  updateUserAvatar: (avatar: string) => void;
  setLoading: (loading: boolean) => void;
  login: (user: User) => void;
  logout: () => void;
  updateActivity: () => void;
  checkAuthStatus: () => boolean;
  initializeAuth: () => Promise<void>;
  fetchUserProfile: () => Promise<User>;
  updateUserProfile: (data: Partial<User>) => Promise<User>;
}

interface PersistedAuthState {
  user: User | null;
  isAuthenticated: boolean;
  lastActivity: number;
}


export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      // Initial state
      user: null,
      isAuthenticated: false,
      isLoading: true,
      lastActivity: Date.now(),
      isInitialized: false,

      // Actions
      setUser: (user) => {
        set((state) => ({
          user,
          isAuthenticated: !!user,
          // Only update lastActivity if it hasn't been updated recently (prevent frequent updates)
          lastActivity:
            state.lastActivity && Date.now() - state.lastActivity < 5000
              ? state.lastActivity
              : Date.now(),
        }));
      },

      updateUserAvatar: (avatar) => {
        set((state) => {
          if (!state.user) {
            return state;
          }

          const updatedUser = {
            ...state.user,
            avatar,
          };

          return {
            ...state,
            user: updatedUser,
            lastActivity: Date.now(),
          };
        });
      },

      // setTokens action removed

      setLoading: (loading) => {
        set({ isLoading: loading });
      },

      login: (user) => {
        set({
          user,
          isAuthenticated: true,
          isLoading: false,
          lastActivity: Date.now(),
          isInitialized: true,
        });
      },

      logout: () => {
        // Clear state - Zustand persist middleware handles localStorage cleanup
        set({
          user: null,
          isAuthenticated: false,
          isLoading: false,
          lastActivity: 0,
          isInitialized: false,
        });
      },

      updateActivity: () => {
        set({ lastActivity: Date.now() });
      },

      checkAuthStatus: () => {
        const { lastActivity, isAuthenticated } = get();

        // If user is not marked authenticated, return false
        if (!isAuthenticated) {
          return false;
        }

        // Check inactivity timeout (30 days)
        const now = Date.now();
        const timeSinceActivity = now - lastActivity;
        const thirtyDays = 30 * 24 * 60 * 60 * 1000;

        if (timeSinceActivity > thirtyDays) {
          get().logout();
          return false;
        }

        // Update last activity timestamp
        set({ lastActivity: now });
        return true;
      },

      // refreshAuthToken action removed

      initializeAuth: async () => {
        const { setLoading, setUser, logout, isInitialized } = get();
        const state = get();

        // 1. If already initialized, ensure loading is false and return
        if (isInitialized) {
          if (state.isLoading) {
            setLoading(false);
          }
          return;
        }

        // 2. Start initialization
          // If we are starting fresh, show loading
          setLoading(true);

          // Check environment
          if (typeof window === "undefined") {
            setLoading(false);
            set({ isInitialized: true });
            return;
          }

          // Skip auth check on login/register pages - user is not expected to be authenticated
          const isOnAuthPage = window.location.pathname.startsWith("/auth/");
          if (isOnAuthPage) {
            setLoading(false);
            set({ isInitialized: true });
            return;
          }

          // Verify session via cookie using /auth/me endpoint
          try {
            // Use apiClient to handle token refresh automatically
            const { apiClient } = await import("@/lib/api-client");
            
            const response = await apiClient.get<User>("/auth/me");
            
            if (response.data) {
              setUser(response.data);
            }
          } catch {
            // If request fails (after retries/refresh), we are not authenticated
            // We expect 401 if user is not logged in, which is fine - just clear state silently
            logout();
          } finally {
             setLoading(false);
             set({ isInitialized: true });
          }
      },

      fetchUserProfile: async () => {
        const { setUser } = get();
        try {
          // Dynamic import to avoid circular dependencies if any
          const { usersApi } = await import("@/lib/api-endpoints");
          const user = await usersApi.getCurrentUser();
          setUser(user);
          return user;
        } catch (error) {
          console.error("Failed to fetch user profile:", error);
          throw error;
        }
      },

      updateUserProfile: async (data: UpdateUserRequest) => {
        const { setUser, user } = get();
        try {
          const { usersApi } = await import("@/lib/api-endpoints");
          // Assuming the API takes the update object directly
          const updatedUser = await usersApi.updateCurrentUser(data);
          setUser({ ...user, ...updatedUser });
          return updatedUser;
        } catch (error) {
          console.error("Failed to update user profile:", error);
          throw error;
        }
      },
    }),
    {
      name: "insight-flow-auth",
      partialize: (state: AuthState): PersistedAuthState => {
        // Validate user object before persisting to avoid corrupted data
        let validatedUser = state.user;
        if (state.user && typeof state.user === "object") {
          // Create a safe copy ensuring required fields are properly typed
          validatedUser = {
            ...state.user,
            // Ensure required string fields are actually strings or fallback to empty string
            email:
              typeof state.user.email === "string"
                ? state.user.email
                : "",
            username:
              typeof state.user.username === "string"
                ? state.user.username
                : "",
            // Optional fields can remain as they are or be undefined
            firstName:
              typeof state.user.firstName === "string"
                ? state.user.firstName
                : undefined,
            lastName:
              typeof state.user.lastName === "string"
                ? state.user.lastName
                : undefined,
          };
        }

        return {
          user: validatedUser,
          isAuthenticated: state.isAuthenticated,
          lastActivity: state.lastActivity,
        };
      },
    },
  ),
);

// ===========================================
// Auth Store Selectors
// ===========================================

export const authSelectors = {
  // Get current user
  getUser: (state: AuthState) => state.user,

  // Get authentication status
  isAuthenticated: (state: AuthState) => state.isAuthenticated,

  // Get loading state
  isLoading: (state: AuthState) => state.isLoading,

  // Check if user has specific role
  hasRole: (role: string) => (state: AuthState) => state.user?.role === role,

  // Check if user has admin role
  isAdmin: (state: AuthState) => state.user?.role === "admin",

  // Check if user has manager role or higher
  isManagerOrHigher: (state: AuthState) => {
    const role = state.user?.role;
    return role === "admin" || role === "manager";
  },

  // Get user initials
  getUserInitials: (state: AuthState): string => {
    if (!state.user) {
      return "U";
    }

    const { firstName, lastName, username, email } = state.user;

    // Strategy 1: First & Last Name
    if (firstName && lastName) {
      return (firstName.charAt(0) + lastName.charAt(0)).toUpperCase();
    }

    // Strategy 2: First Name only
    if (firstName) {
      return firstName.charAt(0).toUpperCase();
    }

    // Strategy 3: Last Name only
    if (lastName) {
      return lastName.charAt(0).toUpperCase();
    }

    // Strategy 4: Username
    if (username) {
      return username.charAt(0).toUpperCase();
    }

    // Strategy 5: Email
    if (email) {
      return email.charAt(0).toUpperCase();
    }

    return "U";
  },

  isUserActive: (state: AuthState) => state.user?.isActive ?? false,
} as const;

// Register the logout handler to avoid circular dependencies
// We can do this safely now that api-client doesn't import auth-store directly
import { registerLogoutHandler } from "@/lib/api-client";

// Register the logout action
if (typeof window !== "undefined") {
  registerLogoutHandler(() => {
    useAuthStore.getState().logout();
  });
}
