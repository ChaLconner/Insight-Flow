// ===========================================
// Zustand Auth Store
// ===========================================

import { isAxiosError, registerLogoutHandler } from "@/lib/api-client";
import { clearAuthenticatedCaches } from "@/lib/auth-cache";
import { create } from "zustand";
import { persist } from "zustand/middleware";
import { authJsonStorage } from "./browser-storage";
import { User, UpdateUserRequest } from "@/types";

interface AuthState {
  // State
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  lastActivity: number;
  rememberMe: boolean;
  isInitialized: boolean;
  hasVerifiedSession: boolean;
  lastVerified: number; // Timestamp of last server-side verification

  // Actions
  setUser: (user: User | null) => void;
  updateUserAvatar: (avatar: string) => void;
  setLoading: (loading: boolean) => void;
  login: (user: User, options?: { rememberMe?: boolean }) => void;
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
  rememberMe: boolean;
  lastVerified: number;
}

let authInitializationPromise: Promise<void> | null = null;
const AUTH_VERIFICATION_TIMEOUT_MS = 8000;
const NO_RETRY_CONFIG = {
  timeout: AUTH_VERIFICATION_TIMEOUT_MS,
  "axios-retry": { retries: 0 },
} as const;

function clearPersistedAuthStorage(): void {
  if (typeof window === "undefined") {
    return;
  }

  try {
    localStorage.removeItem("insight-flow-auth");
    sessionStorage.removeItem("insight-flow-auth");
    localStorage.removeItem("user");
    localStorage.removeItem("access_token");
    localStorage.removeItem("refresh_token");
  } catch {
    // Ignore storage errors; in-memory auth state is the source of truth.
  }
}

function isAuthInvalidationError(error: unknown): boolean {
  if (!isAxiosError(error)) {
    return false;
  }

  const status = error.response?.status;
  return status === 401 || status === 403;
}

type AuthStoreGet = () => AuthState;
type AuthStoreSet = (state: Partial<AuthState>) => void;

function refreshCachedSession(
  setUser: AuthState["setUser"],
  set: AuthStoreSet,
  logout: AuthState["logout"],
): void {
  void import("@/lib/api-client").then(({ apiClient }) => {
    apiClient
      .get<User>("/auth/me", NO_RETRY_CONFIG)
      .then((response) => {
        if (response.data) {
          setUser(response.data);
          set({ hasVerifiedSession: true, lastVerified: Date.now() });
        }
      })
      .catch((error) => {
        if (isAuthInvalidationError(error)) {
          console.warn("⚠️ Cached session invalid, logging out");
          logout();
        }
      });
  });
}

async function verifyCachedSession(
  setUser: AuthState["setUser"],
  setLoading: AuthState["setLoading"],
  set: AuthStoreSet,
  logout: AuthState["logout"],
): Promise<void> {
  setLoading(false);
  set({ isInitialized: true });
  console.log("⏳ Using stale cache, verifying with server...");

  try {
    const { apiClient } = await import("@/lib/api-client");
    const response = await apiClient.get<User>("/auth/me", NO_RETRY_CONFIG);

    if (response.data) {
      setUser(response.data);
      set({ hasVerifiedSession: true, lastVerified: Date.now() });
    }
  } catch (error) {
    if (isAuthInvalidationError(error)) {
      console.warn("⚠️ Cached session invalid, logging out");
      logout();
    } else {
      console.warn("⚠️ Auth verification unavailable, keeping cached session", error);
    }
  }
}

async function fetchInitialSession(
  setUser: AuthState["setUser"],
  setLoading: AuthState["setLoading"],
  set: AuthStoreSet,
  logout: AuthState["logout"],
): Promise<void> {
  setLoading(true);

  try {
    const { apiClient } = await import("@/lib/api-client");
    const response = await apiClient.get<User>("/auth/me", NO_RETRY_CONFIG);

    if (response.data) {
      setUser(response.data);
      set({ hasVerifiedSession: true, lastVerified: Date.now() });
    }
  } catch {
    logout();
  } finally {
    setLoading(false);
    set({ isInitialized: true });
  }
}

async function initializeAuthState(get: AuthStoreGet, set: AuthStoreSet): Promise<void> {
  const {
    setLoading,
    setUser,
    logout,
    isInitialized,
    user,
    isAuthenticated,
    lastVerified,
  } = get();

  if (isInitialized) {
    if (get().isLoading) {
      setLoading(false);
    }
    return;
  }

  if (typeof window === "undefined") {
    setLoading(false);
    set({ isInitialized: true });
    return;
  }

  if (window.location.pathname.startsWith("/auth/")) {
    logout();
    setLoading(false);
    set({ isInitialized: true });
    return;
  }

  const isFreshSession = lastVerified && Date.now() - lastVerified < 5 * 60 * 1000;
  if (isAuthenticated && user && isFreshSession) {
    console.log(
      "✅ Using cached auth (verified",
      Math.round((Date.now() - lastVerified) / 1000),
      "seconds ago)",
    );
    setLoading(false);
    set({ isInitialized: true });
    refreshCachedSession(setUser, set, logout);
    return;
  }

  if (isAuthenticated && user) {
    await verifyCachedSession(setUser, setLoading, set, logout);
    return;
  }

  await fetchInitialSession(setUser, setLoading, set, logout);
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      // Initial state
      user: null,
      isAuthenticated: false,
      isLoading: true,
      lastActivity: Date.now(),
      rememberMe: false,
      isInitialized: false,
      hasVerifiedSession: false,
      lastVerified: 0,

      // Actions
      setUser: (user) => {
        const previousUser = get().user;
        const accountChanged = previousUser?.id !== user?.id;
        if (accountChanged && typeof window !== "undefined") {
          // Auth hydration, expiry, and legacy callers can bypass login/logout.
          // Treat an identity change as a full authenticated-cache boundary.
          void clearAuthenticatedCaches();
        }

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

      login: (user, options = {}) => {
        if (typeof window !== "undefined") {
          // Keep direct store consumers safe too; authActions also clears the
          // same registries before the normal login flow commits new state.
          void clearAuthenticatedCaches();
        }

        set({
          user,
          isAuthenticated: true,
          isLoading: false,
          lastActivity: Date.now(),
          rememberMe: options.rememberMe === true,
          lastVerified: Date.now(),
          isInitialized: true,
          hasVerifiedSession: true,
        });
      },

      logout: () => {
        if (typeof window !== "undefined") {
          // Session expiry and legacy callers can reach the store directly,
          // bypassing authActions. Clear all authenticated caches before the
          // account state changes so the next account cannot inherit them.
          void clearAuthenticatedCaches();
        }

        // Clear in-memory state and remove persisted/legacy auth storage.
        set({
          user: null,
          isAuthenticated: false,
          isLoading: false,
          lastActivity: 0,
          rememberMe: false,
          lastVerified: 0,
          isInitialized: false,
          hasVerifiedSession: false,
        });

        clearPersistedAuthStorage();

        if (typeof window !== "undefined" && typeof window.queueMicrotask === "function") {
          window.queueMicrotask(clearPersistedAuthStorage);
        }
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
        if (authInitializationPromise) {
          return authInitializationPromise;
        }

        authInitializationPromise = initializeAuthState(get, set);

        try {
          await authInitializationPromise;
        } finally {
          authInitializationPromise = null;
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
      storage: authJsonStorage,
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
          rememberMe: state.rememberMe,
          lastVerified: state.lastVerified,
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

  hasVerifiedSession: (state: AuthState) => state.hasVerifiedSession,

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

// Register the logout action
if (typeof window !== "undefined") {
  registerLogoutHandler(() => {
    useAuthStore.getState().logout();
  });
}
