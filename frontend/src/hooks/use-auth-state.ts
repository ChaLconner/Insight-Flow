// ===========================================
// useAuthState Hook
// ===========================================

import { useEffect, useRef } from 'react';
import { useAuthStore, authSelectors } from '@/stores/auth-store';
import { authActions } from '@/stores/auth-actions';

import { User } from '@/types';



// Hook for auth state management with React Query integration
export const useAuthState = () => {
  // Use granular selectors to avoid unnecessary re-renders
  // We strictly avoid selecting the entire store or properties like lastActivity that update frequently
  const user = useAuthStore(authSelectors.getUser);
  const isAuthenticated = useAuthStore(authSelectors.isAuthenticated);
  const isLoading = useAuthStore(authSelectors.isLoading);

  // Derived state via selectors
  const userInitials = useAuthStore(authSelectors.getUserInitials);
  const isAdmin = useAuthStore(authSelectors.isAdmin);
  const isManagerOrHigher = useAuthStore(authSelectors.isManagerOrHigher);
  const isUserActive = useAuthStore(authSelectors.isUserActive);

  // Actions - stable references
  const checkAuthStatus = useAuthStore(state => state.checkAuthStatus);
  const updateActivity = useAuthStore(state => state.updateActivity);
  const setUser = useAuthStore(state => state.setUser);
  const setLoading = useAuthStore(state => state.setLoading);

  const initializationRef = useRef(false);

  // Initialize auth on mount
  useEffect(() => {
    let mounted = true;

    const init = async () => {
      // Prevent multiple initializations
      if (initializationRef.current) { return; }
      initializationRef.current = true;

      // Initialize auth checks for session via cookie
      try {

        await authActions.initializeAuth();
      } catch (error) {
        console.error('❌ Failed to initialize auth:', error);
        if (mounted && isLoading) {
          setLoading(false);
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
    if (isLoading) {
      const safetyTimeout = setTimeout(() => {
        console.warn('⚠️ Auth check timed out, forcing loading to false');
        setLoading(false);
      }, 7000);

      return () => clearTimeout(safetyTimeout);
    }
  }, [isLoading, setLoading]);

  return {
    // State
    user,
    isAuthenticated,
    isLoading,
    error: null,

    // Computed values
    userInitials,
    isAdmin,
    isManagerOrHigher,
    isUserActive,

    // Actions
    login: authActions.loginWithResponse,
    logout: authActions.logoutAndRedirect,
    updateActivity,
    checkAuthStatus,

    // Store methods for advanced usage
    setUser,
    setLoading,
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
  } = useAuthState();

  return {
    user,
    isAuthenticated,
    isLoading,
    userInitials,
    isAdmin,
    isManagerOrHigher,
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
  } = useAuthState();

  // Use ref for timeout to avoid sharing state between hook instances
  const redirectTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  useEffect(() => {
    // Add minimal debouncing to prevent rapid redirects (optimized for speed)
    if (!redirectTimeoutRef.current) {
      const timeoutId = setTimeout(() => {
        // Fast path: if authenticated and has user, no need to check further
        if (isAuthenticated && user) {
          return;
        }

        // If not authenticated and not loading, redirect to login immediately
        if ((!isAuthenticated || !user) && !isLoading && typeof window !== 'undefined') {
          // Check if we are already on the login page to prevent loops
          const path = window.location.pathname;
          if (path.startsWith('/auth/login') || path.startsWith('/auth/register')) {
            return;
          }

          // Prevent infinite redirect loops
          const isAuthPage = path.startsWith('/auth/login') || path.startsWith('/auth/register');
          if (!isAuthPage) {
            // Use replace to avoid history stack issues
            console.warn('🔒 useRequireAuth: Redirecting to login (missing auth)');
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
      document.addEventListener(event, handleActivity, { capture: true, passive: true });
    });

    return () => {
      clearTimeout(updateActivityTimer);
      clearTimeout(checkSessionTimer);
      activityEvents.forEach(event => {
        document.removeEventListener(event, handleActivity, { capture: true } as any);
      });
    };
  }, [updateActivity, checkAuthStatus, timeoutMinutes]);

  return { updateActivity };
};