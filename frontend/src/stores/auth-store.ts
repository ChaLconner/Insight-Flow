// ===========================================
// Zustand Auth Store
// ===========================================

import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { User, AuthResponse } from '@/types';

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

// Global flag removed to prevent race conditions
// let initializationPromise: Promise<void> | null = null;

// Export function to reset global initialization flag (for auth-actions)
export const resetGlobalAuthInitialization = () => {
  // No-op as global flag is removed
};

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
          lastActivity: state.lastActivity && (Date.now() - state.lastActivity) < 5000 ? state.lastActivity : Date.now(),
        }));
      },

      updateUserAvatar: (avatar) => {
        set((state) => {
          if (!state.user) {
            return state;
          }

          const updatedUser = {
            ...state.user,
            avatar
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
        // Clear localStorage user data
        // Clear localStorage user data - Removed as we use Zustand persist which handles this
        // and we want to rely on state management not manual API
        if (typeof window !== 'undefined') {
          // We explicitly DO NOT want to manually clear 'user' from localStorage
          // because Zustand persist middleware manages the 'insight-flow-auth' key.
          // Clearing 'user' (if it existed from old code) is fine, but we should strictly rely on the store.
        }

        // Clear state
        set({
          user: null,
          isAuthenticated: false,
          isLoading: false,
          lastActivity: 0,
          isInitialized: false,
        });

        // Reset global initialization flag to allow re-initialization
        resetGlobalAuthInitialization();
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

        // Check inactivity timeout (30 minutes)
        const now = Date.now();
        const timeSinceActivity = now - lastActivity;
        const thirtyMinutes = 30 * 60 * 1000;

        if (timeSinceActivity > thirtyMinutes) {
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
          if (state.isLoading) { setLoading(false); }
          return;
        }

        // 2. Start initialization
        try {
          // If we are starting fresh, show loading
          setLoading(true);

          // Check environment
          if (typeof window === 'undefined') {
            return;
          }

          const apiUrl = (await import('@/lib/constants')).API_CONFIG.BASE_URL;

          // Verify session via cookie using /auth/me endpoint
          try {
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), 3000);

            // Fetch with credentials (cookies)
            const resp = await fetch(`${apiUrl}/auth/me`, {
              method: 'GET',
              // headers: { 'Authorization': ... }, // No header needed, cookies sent automatically? 
              // Wait, native fetch needs credentials: 'include'
              credentials: 'include',
              signal: controller.signal
            });
            clearTimeout(timeoutId);

            if (resp.ok) {
              const userData = await resp.json();
              setUser(userData);
            } else {
              // 401 or 403 means cookies invalid or missing
              if (resp.status === 401 || resp.status === 403) {
                logout();
              }
            }
          } catch (fetchError: any) {
            if (fetchError.name !== 'AbortError') {
              // Network error or other
              console.warn('Auth check network error, assuming not authenticated');
              logout();
            }
          }
        } catch (error) {
          console.error('🏪 AuthStore: Error initializing auth:', error);
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
          const { usersApi } = await import('@/lib/api-endpoints');
          const user = await usersApi.getCurrentUser();
          setUser(user);
          return user;
        } catch (error) {
          console.error('Failed to fetch user profile:', error);
          throw error;
        }
      },

      updateUserProfile: async (data: Partial<User>) => {
        const { setUser, user } = get();
        try {
          const { usersApi } = await import('@/lib/api-endpoints');
          // Assuming the API takes the update object directly
          const updatedUser = await usersApi.updateCurrentUser(data as any);
          setUser({ ...user, ...updatedUser });
          return updatedUser;
        } catch (error) {
          console.error('Failed to update user profile:', error);
          throw error;
        }
      },

    }),
    {
      name: 'insight-flow-auth',
      partialize: (state: AuthState): PersistedAuthState => {
        // Validate user object before persisting to avoid corrupted data
        let validatedUser = state.user;
        if (state.user && typeof state.user === 'object') {
          // Create a safe copy ensuring required fields are properly typed
          validatedUser = {
            ...state.user,
            // Ensure required string fields are actually strings or fallback to empty string
            email: typeof state.user.email === 'string' ? state.user.email : (state.user.email || ''),
            username: typeof state.user.username === 'string' ? state.user.username : (state.user.username || ''),
            // Optional fields can remain as they are or be undefined
            firstName: typeof state.user.firstName === 'string' ? state.user.firstName : (state.user.firstName || undefined),
            lastName: typeof state.user.lastName === 'string' ? state.user.lastName : (state.user.lastName || undefined),
          };
        }

        return {
          user: validatedUser,
          isAuthenticated: state.isAuthenticated,
          lastActivity: state.lastActivity,
        };
      },
    }
  )
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
  hasRole: (role: string) => (state: AuthState) =>
    state.user?.role === role,

  // Check if user has admin role
  isAdmin: (state: AuthState) =>
    state.user?.role === 'admin',

  // Check if user has manager role or higher
  isManagerOrHigher: (state: AuthState) => {
    const role = state.user?.role;
    return role === 'admin' || role === 'manager';
  },

  // Get user initials
  getUserInitials: (state: AuthState): string => {
    if (!state.user) {
      return 'U';
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

    return 'U';
  },

  isUserActive: (state: AuthState) => state.user?.isActive ?? false,
} as const;

// Register the logout handler to avoid circular dependencies
// We can do this safely now that api-client doesn't import auth-store directly
import { registerLogoutHandler } from '@/lib/api-client';

// Register the logout action
if (typeof window !== 'undefined') {
  registerLogoutHandler(() => {
    useAuthStore.getState().logout();
  });
}