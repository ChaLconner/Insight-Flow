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
  accessToken: string | null;
  refreshToken: string | null;
  lastActivity: number;
  isInitialized: boolean;

  // Actions
  setUser: (user: User) => void;
  setTokens: (accessToken: string, refreshToken: string) => void;
  setLoading: (loading: boolean) => void;
  login: (user: User, accessToken: string, refreshToken: string) => void;
  logout: () => void;
  updateActivity: () => void;
  checkAuthStatus: () => boolean;
  refreshAuthToken: (newToken: string, newRefreshToken: string) => void;
  initializeAuth: () => Promise<void>;
}

interface PersistedAuthState {
  user: User | null;
  isAuthenticated: boolean;
  accessToken: string | null;
  refreshToken: string | null;
  lastActivity: number;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      // Initial state
      user: null,
      isAuthenticated: false,
      isLoading: true,
      accessToken: null,
      refreshToken: null,
      lastActivity: Date.now(),
      isInitialized: false,

      // Actions
      setUser: (user) => {
        console.log('🏪 AuthStore: Setting user:', user);
        set((state) => ({
          user,
          isAuthenticated: !!user,
          // Only update lastActivity if it hasn't been updated recently (prevent frequent updates)
          lastActivity: state.lastActivity && (Date.now() - state.lastActivity) < 5000 ? state.lastActivity : Date.now(),
        }));
      },

      setTokens: (accessToken, refreshToken) => {
        console.log('🏪 AuthStore: Setting tokens');
        set((state) => ({
          accessToken,
          refreshToken,
          // Only update lastActivity if it hasn't been updated recently (prevent frequent updates)
          lastActivity: state.lastActivity && (Date.now() - state.lastActivity) < 5000 ? state.lastActivity : Date.now(),
        }));
      },

      setLoading: (loading) => {
        set({ isLoading: loading });
      },

      login: (user, accessToken, refreshToken) => {
        console.log('🏪 AuthStore: Login called with:', {
          user: user?.email,
          hasAccessToken: !!accessToken,
          hasRefreshToken: !!refreshToken
        });
        set({
          user,
          accessToken,
          refreshToken,
          isAuthenticated: true,
          isLoading: false,
          lastActivity: Date.now(),
          isInitialized: true,
        });
        console.log('🏪 AuthStore: Login completed');
      },

      logout: () => {
        // Clear localStorage tokens
        if (typeof window !== 'undefined') {
          localStorage.removeItem('access_token');
          localStorage.removeItem('refresh_token');
          localStorage.removeItem('user');
          try {
            localStorage.removeItem('insight-flow-auth');
          } catch (e) {
            console.warn('Failed to remove persisted auth', e);
          }
        }

        // Clear state
        set({
          user: null,
          accessToken: null,
          refreshToken: null,
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
        if (!isAuthenticated) return false;

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

      refreshAuthToken: (newToken, newRefreshToken) => {
        set({
          accessToken: newToken,
          refreshToken: newRefreshToken,
          lastActivity: Date.now(),
        });
      },

      initializeAuth: async () => {
        const { setLoading, setUser, logout } = get();
        const state = get();
        
        // 🆔 Add unique call ID for tracking
        const callId = `auth_init_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
        const startTime = Date.now();

        console.log(`🔍 AuthStore: initializeAuth called [${callId}] at`, new Date().toISOString(), {
          isInitialized: state.isInitialized,
          isAuthenticated: state.isAuthenticated,
          isLoading: state.isLoading,
          hasUser: !!state.user,
          stackTrace: new Error().stack?.split('\n').slice(1, 4).join('\n')
        });

        // Enhanced check for multiple initialization with better performance
        if ((globalThis as any).__auth_initializing) {
          console.log(`❌ AuthStore: Initialization already in progress [${callId}], skipping`);
          return;
        }

        // Fast check for already initialized state
        if (state.isInitialized && state.isAuthenticated && state.user) {
          console.log(`✅ AuthStore: Already initialized [${callId}], skipping`);
          return;
        }

        (globalThis as any).__auth_initializing = true;
        console.log(`🏁 AuthStore: Starting initialization [${callId}] at`, new Date().toISOString());

        try {
          // Only set loading to true if we are not already authenticated
          // This prevents the "flicker" (Content -> Loading -> Content) when we have a persisted session
          if (!state.isAuthenticated) {
            setLoading(true);
          }

          // Check if we're in browser environment
          if (typeof window === 'undefined') {
            setLoading(false);
            (globalThis as any).__auth_initializing = false;
            return;
          }

          const apiUrl = (await import('@/lib/constants')).API_CONFIG.BASE_URL;

          // Bearer token flow: read access token from localStorage or persisted store
          let token = localStorage.getItem('access_token') || localStorage.getItem('accessToken');
          if (!token) {
            const persisted = localStorage.getItem('insight-flow-auth');
            if (persisted) {
              try {
                const parsed = JSON.parse(persisted);
                const stateCandidate = parsed?.state ?? parsed;
                token = stateCandidate?.accessToken || stateCandidate?.access_token || null;
              } catch (e) {
                // ignore
              }
            }
          }

          if (!token) {
            console.log('🏪 AuthStore: No token found, setting loading to false');
            setLoading(false);
            (globalThis as any).__auth_initializing = false;
            return;
          } else {
            console.log('🏪 AuthStore: Found token, calling /auth/me');
            try {
              const resp = await fetch(`${apiUrl}/auth/me`, {
                method: 'GET',
                headers: { 'Authorization': `Bearer ${token}` },
              });

              if (resp.ok) {
                const userData = await resp.json();
                console.log('🏪 AuthStore: /auth/me response received:', userData.email);
                setUser(userData);
              } else {
                console.log('🏪 AuthStore: /auth/me failed with status:', resp.status);

                // If unauthorized, clear everything to prevent loops
                if (resp.status === 401 || resp.status === 403) {
                  console.log('🏪 AuthStore: Invalid token, clearing auth state');

                  // Only clear if we actually have tokens to clear to prevent loops
                  const currentToken = localStorage.getItem('access_token') || localStorage.getItem('accessToken');
                  if (currentToken) {
                    try {
                      localStorage.removeItem('insight-flow-auth');
                    } catch (e) {
                      console.warn('Failed to remove persisted auth', e);
                    }
                    logout();
                  } else {
                    // Just ensure state is clean without triggering full logout flow
                    setLoading(false);
                  }
                } else {
                  try { localStorage.removeItem('user'); } catch { }
                }
              }
            } catch (fetchError) {
              console.error('🏪 AuthStore: Network error during /auth/me fetch:', fetchError);
              // Don't clear auth on network error, just stop loading
            }
          }
        } catch (error) {
          console.error('🏪 AuthStore: Error initializing auth:', error);
        } finally {
          const endTime = Date.now();
          const duration = endTime - startTime;
          console.log(`🎯 AuthStore: Completed initialization [${callId}] in ${duration}ms, setting loading to false`);
          setLoading(false);
          set({ isInitialized: true });
          (globalThis as any).__auth_initializing = false;
          console.log(`🔚 AuthStore: End [${callId}]`);
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
            firstName: typeof state.user.firstName === 'string' ? state.user.firstName : undefined,
            lastName: typeof state.user.lastName === 'string' ? state.user.lastName : undefined,
          };
        }

        return {
          user: validatedUser,
          accessToken: state.accessToken,
          refreshToken: state.refreshToken,
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

  // Get access token
  getAccessToken: (state: AuthState) => state.accessToken,

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

  // Get user initials with comprehensive safety checks
  getUserInitials: (state: AuthState): string => {
    try {
      // Safety check for undefined/null state
      if (!state || !state.user) {
        return 'U';
      }

      // Get user object and make sure it's an object
      const user = state.user;
      if (!user || typeof user !== 'object') {
        return 'U';
      }

      // Helper function to safely extract first character with comprehensive validation
      const safeCharAt = (str: any, index: number): string => {
        try {
          // Check for null, undefined, or not a string-like value
          if (str == null) {
            return '';
          }

          // Convert to string safely and handle edge cases
          let strValue: string;
          if (typeof str === 'string') {
            strValue = str;
          } else if (typeof str === 'number') {
            strValue = String(str);
          } else if (typeof str === 'boolean') {
            strValue = str ? 'true' : 'false';
          } else if (str instanceof Date) {
            strValue = str.toString();
          } else if (Array.isArray(str)) {
            strValue = str.join('');
          } else if (typeof str === 'object') {
            // Try to get string representation or first meaningful property
            strValue = str.toString ? str.toString() : JSON.stringify(str);
          } else {
            strValue = String(str);
          }

          // Validate string and length
          if (typeof strValue !== 'string' || !strValue.trim()) {
            return '';
          }

          // Check if string has the requested character
          if (strValue.length > index && index >= 0) {
            return strValue.charAt(index);
          }

          return '';
        } catch (error) {
          console.warn('Error in safeCharAt:', error, 'input:', str);
          return '';
        }
      };

      // Extract and validate user properties
      const firstName = user.firstName;
      const lastName = user.lastName;
      const username = user.username;
      const email = user.email;

      // Get first characters safely with additional validation
      const firstInitial = safeCharAt(firstName, 0);
      const lastInitial = safeCharAt(lastName, 0);
      const usernameInitial = safeCharAt(username, 0);
      const emailInitial = safeCharAt(email, 0);

      // Combine initials based on available data with fallback logic
      if (firstInitial && lastInitial) {
        return `${firstInitial}${lastInitial}`.toUpperCase();
      }
      if (firstInitial) {
        return firstInitial.toUpperCase();
      }
      if (lastInitial) {
        return lastInitial.toUpperCase();
      }
      if (usernameInitial) {
        return usernameInitial.toUpperCase();
      }
      if (emailInitial) {
        return emailInitial.toUpperCase();
      }

      return 'U'; // Default initial if no other info is available
    } catch (error) {
      console.error('Error getting user initials:', error);
      return 'U'; // Return default initials if there's an error
    }
  },

  // Check if user is active
  isUserActive: (state: AuthState): boolean =>
    state.user?.isActive ?? false,
} as const;

