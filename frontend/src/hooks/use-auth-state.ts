// ===========================================
// useAuthState Hook
// ===========================================

import { useEffect } from 'react';
import { useAuthStore, authSelectors } from '@/stores/auth-store';
import { authActions } from '@/stores/auth-actions';
// Removed: import { useAuth as useAuthQuery } from '@/hooks/use-api';
import { User } from '@/types';

// Module-level redirect timeout used by useRequireAuth to avoid attaching
// properties to the hook function (keeps TypeScript happy).
let _useRequireAuthRedirectTimeout: NodeJS.Timeout | null = null;

// Hook for auth state management with React Query integration
export const useAuthState = () => {
  // Zustand store state
  const store = useAuthStore();

  // DON'T use React Query for initial auth check - it causes loops
  // React Query will be used only after successful login
  // const { data: user, isLoading: queryLoading, error: queryError } = useAuthQuery();

  // Initialize auth on mount - OPTIMIZED for faster response
  useEffect(() => {
    let mounted = true;
    let timeoutId: NodeJS.Timeout;

    const initAuth = async () => {
      // 🚫 Prevent rapid successive calls with enhanced debouncing
      const now = Date.now();
      if ((useAuthState as any)._lastInitCall && (now - (useAuthState as any)._lastInitCall) < 1500) {
        console.log(`⏱️ useAuthState: Debouncing rapid calls, last call was`, now - (useAuthState as any)._lastInitCall, 'ms ago');
        return;
      }
      (useAuthState as any)._lastInitCall = now;

      const callId = `hook_init_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
      
      // Enhanced check for already initialized state with user validation
      if (store.isInitialized && store.isAuthenticated && store.user) {
        console.log(`✅ useAuthState: Already fully initialized [${callId}], skipping`);
        return;
      }

      // Prevent multiple simultaneous initializations with better flag management
      if ((useAuthState as any)._isInitializing) {
        console.log(`⏭️ useAuthState: Already initializing [${callId}], skipping`);
        return;
      }

      (useAuthState as any)._isInitializing = true;
      console.log(`🚀 useAuthState: Starting init [${callId}] at`, new Date().toISOString());

      // Reduced delay for faster response
      timeoutId = setTimeout(async () => {
        if (!mounted) {
          (useAuthState as any)._isInitializing = false;
          console.log(`⚠️ useAuthState: Component unmounted [${callId}], aborting`);
          return;
        }

        // Enhanced token detection with combined checks
        const hasToken = typeof window !== 'undefined' && (() => {
          const token = localStorage.getItem('access_token') || 
                       localStorage.getItem('accessToken') ||
                       localStorage.getItem('insight-flow-auth');
          
          if (token && token.includes('access')) {
            try {
              const parsed = JSON.parse(token);
              return !!(parsed?.state?.accessToken || parsed?.state?.access_token || 
                       parsed?.accessToken || parsed?.access_token);
            } catch (e) {
              return true; // Assume valid if can't parse
            }
          }
          return false;
        })();

        console.log(`🔍 useAuthState: Initialize auth check [${callId}]`, {
          hasToken,
          isInitialized: store.isInitialized,
          isAuthenticated: store.isAuthenticated,
          hasUser: !!store.user,
          timestamp: new Date().toISOString(),
          isMounted: mounted
        });

        if (hasToken && mounted) {
          console.log(`📞 useAuthState: Calling authActions.initializeAuth [${callId}]`);
          await authActions.initializeAuth();
          console.log(`✅ useAuthState: authActions.initializeAuth completed [${callId}]`);
        } else if (mounted) {
          console.log(`❌ useAuthState: No token found [${callId}], setting loading to false`);
          store.setLoading(false);
        }

        (useAuthState as any)._isInitializing = false;
        console.log(`🔚 useAuthState: End [${callId}]`);
      }, 100); // Reduced to 100ms for much faster response

    };

    initAuth();

    return () => {
      mounted = false;
      if (timeoutId) {
        clearTimeout(timeoutId);
      }
      (useAuthState as any)._isInitializing = false;
    };
  }, []); // Empty deps - run only once on mount

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

  // Log state changes - Only log meaningful changes and reduce frequency
  useEffect(() => {
    const now = Date.now();
    // Throttle logging to prevent console spam
    if (!(useAuthState as any)._lastLogTime || (now - (useAuthState as any)._lastLogTime) > 2000) {
      console.log('🔐 Auth State Updated:', {
        isAuthenticated,
        isLoading,
        hasUser: !!currentUser,
        timestamp: new Date().toISOString()
      });
      (useAuthState as any)._lastLogTime = now;
    }
  }, [isAuthenticated, isLoading]); // Only track meaningful changes

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

  useEffect(() => {
    const now = new Date().toISOString();
    console.log('🔐 useRequireAuth: checking auth', {
      isAuthenticated,
      isLoading,
      hasUser: !!user,
      timestamp: now
    });

    // Add minimal debouncing to prevent rapid redirects (optimized for speed)
    if (!_useRequireAuthRedirectTimeout) {
      const timeoutId = setTimeout(() => {
        // Fast path: if authenticated and has user, no need to check further
        if (isAuthenticated && user) {
          return;
        }
        
        // If not authenticated and not loading, redirect to login immediately
        if (!isAuthenticated && !user && !isLoading && typeof window !== 'undefined') {
          // Check if we are already on the login page to prevent loops
          const path = window.location.pathname;
          if (path.startsWith('/auth/login') || path.startsWith('/auth/register')) {
            return;
          }

          console.log('🔐 useRequireAuth: Redirecting to login - not authenticated');

          // Prevent infinite redirect loops
          const isAuthPage = path.startsWith('/auth/login') || path.startsWith('/auth/register');
          if (!isAuthPage) {
            // Use replace to avoid history stack issues
            window.location.replace('/auth/login');
          }
        }
        
        _useRequireAuthRedirectTimeout = null;
      }, 200); // Reduced to 200ms for faster response
      
      _useRequireAuthRedirectTimeout = timeoutId;
    }
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