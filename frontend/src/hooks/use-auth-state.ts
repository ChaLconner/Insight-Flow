// ===========================================
// useAuthState Hook
// ===========================================

import { useEffect, useRef } from 'react';
import { useAuthStore, authSelectors } from '@/stores/auth-store';
import { authActions } from '@/stores/auth-actions';

import { User } from '@/types';



// Hook for auth state management with React Query integration
export const useAuthState = () => {
  // Zustand store state
  const store = useAuthStore();
  const initializationRef = useRef(false);

  // Initialize auth on mount - Simplified to rely on store singleton
  useEffect(() => {
    let mounted = true;

    const init = async () => {
      // Prevent multiple initializations
      if (initializationRef.current) { return; }
      initializationRef.current = true;

      // Check if we have a token in storage
      const hasToken = typeof window !== 'undefined' && !!useAuthStore.getState().accessToken;

      if (hasToken) {
        // Initialize auth directly without waiting for backend health check
        // This prevents infinite loading states
        try {
          console.log('🔄 Initializing auth directly...');
          await authActions.initializeAuth();
        } catch (error) {
          console.error('❌ Failed to initialize auth:', error);
          if (mounted && store.isLoading) {
            store.setLoading(false);
          }
        }
      } else {
        // No token, ensure loading is false
        if (mounted && store.isLoading) {
          store.setLoading(false);
        }
      }
    };

    init();

    return () => {
      mounted = false;
    };
  }, []); // Empty deps - run only once on mount

  // Safety timeout to prevent infinite loading state
  useEffect(() => {
    if (store.isLoading) {
      const safetyTimeout = setTimeout(() => {
        console.warn('⚠️ Auth check timed out, forcing loading to false');
        store.setLoading(false);
      }, 7000);

      return () => clearTimeout(safetyTimeout);
    }
  }, [store.isLoading, store.setLoading]);

  // Determine overall loading state
  const overallIsLoading = store.isLoading;

  // Selectors with safety checks - only compute if not loading/error
  const isAuthenticated = store && typeof authSelectors.isAuthenticated === 'function'
    ? (() => {
      try {
        return authSelectors.isAuthenticated(store);
      } catch (error) {
        console.error('Error in isAuthenticated selector:', error);
        return false;
      }
    })()
    : false;
  const isLoading = overallIsLoading;
  const currentUser = store && typeof authSelectors.getUser === 'function'
    ? (() => {
      try {
        return authSelectors.getUser(store);
      } catch (error) {
        console.error('Error in getUser selector:', error);
        return null;
      }
    })()
    : null;
  const userInitials = store && typeof authSelectors.getUserInitials === 'function' && store.user
    ? (() => {
      try {
        return authSelectors.getUserInitials(store);
      } catch (error) {
        console.error('Error in getUserInitials selector:', error);
        return 'U';
      }
    })()
    : 'U';
  const isAdmin = store && typeof authSelectors.isAdmin === 'function'
    ? (() => {
      try {
        return authSelectors.isAdmin(store);
      } catch (error) {
        console.error('Error in isAdmin selector:', error);
        return false;
      }
    })()
    : false;
  const isManagerOrHigher = store && typeof authSelectors.isManagerOrHigher === 'function'
    ? (() => {
      try {
        return authSelectors.isManagerOrHigher(store);
      } catch (error) {
        console.error('Error in isManagerOrHigher selector:', error);
        return false;
      }
    })()
    : false;
  const isUserActive = store && typeof authSelectors.isUserActive === 'function'
    ? (() => {
      try {
        return authSelectors.isUserActive(store);
      } catch (error) {
        console.error('Error in isUserActive selector:', error);
        return false;
      }
    })()
    : false;

  // Actions
  const login = authActions.loginWithResponse;
  const logout = authActions.logoutAndRedirect;
  const updateActivity = store.updateActivity;
  const checkAuthStatus = store.checkAuthStatus;

  return {
    // State
    user: currentUser,
    isAuthenticated,
    isLoading: isLoading,
    accessToken: store.accessToken, // Return access token
    error: null,

    // Computed values
    userInitials,
    isAdmin,
    isManagerOrHigher,
    isUserActive,

    // Actions
    login,
    logout,
    updateActivity,
    checkAuthStatus,

    // Store methods for advanced usage
    setUser: store.setUser,
    setTokens: store.setTokens,
    setLoading: store.setLoading,
    refreshAuthToken: store.refreshAuthToken,
  };
};

// ===========================================
// useAuth - Simplified hook for common usage
// ===========================================

export const useAuth = () => {
  const {
    user,
    isAuthenticated,
    isLoading,
    userInitials,
    isAdmin,
    isManagerOrHigher,
    accessToken,
  } = useAuthState();

  return {
    user,
    isAuthenticated,
    isLoading,
    userInitials,
    isAdmin,
    isManagerOrHigher,
    accessToken,
  };
};

// ===========================================
// useRequireAuth - Hook for protected routes
// ===========================================

export const useRequireAuth = () => {
  const {
    user,
    isAuthenticated,
    isLoading,
    logout,
    accessToken,
  } = useAuthState();

  // Use ref for timeout to avoid sharing state between hook instances
  const redirectTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  useEffect(() => {
    // Add minimal debouncing to prevent rapid redirects (optimized for speed)
    if (!redirectTimeoutRef.current) {
      const timeoutId = setTimeout(() => {
        // Fast path: if authenticated and has user AND token, no need to check further
        if (isAuthenticated && user && accessToken) {
          return;
        }

        // If not authenticated (or no token) and not loading, redirect to login immediately
        if ((!isAuthenticated || !user || !accessToken) && !isLoading && typeof window !== 'undefined') {
          // Check if we are already on the login page to prevent loops
          const path = window.location.pathname;
          if (path.startsWith('/auth/login') || path.startsWith('/auth/register')) {
            return;
          }

          // Prevent infinite redirect loops
          const isAuthPage = path.startsWith('/auth/login') || path.startsWith('/auth/register');
          if (!isAuthPage) {
            // Use replace to avoid history stack issues
            console.warn('🔒 useRequireAuth: Redirecting to login (missing auth/token)');
            window.location.replace('/auth/login');
          }
        }

        redirectTimeoutRef.current = null;
      }, 200); // Reduced to 200ms for faster response

      redirectTimeoutRef.current = timeoutId;
    }

    return () => {
      if (redirectTimeoutRef.current) {
        clearTimeout(redirectTimeoutRef.current);
        redirectTimeoutRef.current = null;
      }
    };
  }, [isAuthenticated, isLoading, user]); // Include user in deps with debouncing

  // Return auth state for use in components
  return {
    isAuthenticated,
    isLoading,
    user,
  };
};

// ===========================================
// useRoleGuard - Hook for role-based access control
// ===========================================

export const useRoleGuard = (requiredRole: string | string[]) => {
  const { user, isAuthenticated } = useAuthState();

  const hasRequiredRole = () => {
    if (!user || !isAuthenticated) {
      return false;
    }
    const roles = Array.isArray(requiredRole) ? requiredRole : [requiredRole];
    return roles.includes(user.role);
  };

  return {
    hasRequiredRole: hasRequiredRole(),
    userRole: user?.role,
    isAuthenticated,
  };
};

// ===========================================
// usePermissions - Hook for granular permissions
// ===========================================

export const usePermissions = () => {
  const { user } = useAuthState();

  const permissions = {
    // User Management
    canCreateUsers: user?.role === 'admin',
    canEditUsers: user?.role === 'admin',
    canDeleteUsers: user?.role === 'admin',
    canManageUserRoles: user?.role === 'admin',

    // Project Management
    canCreateProjects: ['admin', 'manager'].includes(user?.role || ''),
    canEditProjects: ['admin', 'manager'].includes(user?.role || ''),
    canDeleteProjects: user?.role === 'admin',
    canManageProjectMembers: ['admin', 'manager'].includes(user?.role || ''),

    // Task Management
    canCreateTasks: true, // All authenticated users
    canEditOwnTasks: true, // Users can edit tasks they created or assigned to
    canEditAllTasks: ['admin', 'manager'].includes(user?.role || ''),
    canDeleteTasks: ['admin', 'manager'].includes(user?.role || ''),
    canAssignTasks: ['admin', 'manager'].includes(user?.role || ''),

    // Analytics & Reports
    canViewAnalytics: ['admin', 'manager'].includes(user?.role || ''),
    canExportReports: ['admin', 'manager'].includes(user?.role || ''),

    // Settings
    canManageSettings: user?.role === 'admin',
    canManageSystemSettings: user?.role === 'admin',
  };

  const checkPermission = (permission: keyof typeof permissions): boolean => {
    return permissions[permission] || false;
  };

  return {
    permissions,
    checkPermission,
    userRole: user?.role,
  };
};

// ===========================================
// useSessionTimeout - Hook for session management
// ===========================================

export const useSessionTimeout = (timeoutMinutes: number = 30) => {
  const { updateActivity, checkAuthStatus } = useAuthState();

  useEffect(() => {
    const timeoutMs = timeoutMinutes * 60 * 1000;

    const updateActivityTimer = setTimeout(() => {
      updateActivity();
    }, 5000); // Update every 5 minutes

    const checkSessionTimer = setTimeout(() => {
      if (!checkAuthStatus()) {
        // Session expired, logout
        useAuthStore.getState().logout();
        window.location.href = '/auth/login?expired=true';
      }
    }, timeoutMs);

    // Activity listeners
    const activityEvents = ['mousedown', 'mousemove', 'keypress', 'scroll', 'touchstart'];

    const handleActivity = () => {
      updateActivity();
    };

    activityEvents.forEach(event => {
      document.addEventListener(event, handleActivity, true);
    });

    return () => {
      clearTimeout(updateActivityTimer);
      clearTimeout(checkSessionTimer);
      activityEvents.forEach(event => {
        document.removeEventListener(event, handleActivity, true);
      });
    };
  }, [updateActivity, checkAuthStatus, timeoutMinutes]);

  return { updateActivity };
};