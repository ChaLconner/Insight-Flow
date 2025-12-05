// ===========================================
// Auth Actions (Separated to avoid circular dependency)
// ===========================================

import { useAuthStore, resetGlobalAuthInitialization } from './auth-store';
import { AuthResponse } from '@/types';

// Track initialization state to prevent duplicate calls
// Track initialization state to prevent duplicate calls
// (Moved to auth-store.ts)

// Auth actions that depend on the store but don't create circular imports
export const authActions = {
  // Login function that stores data in localStorage and updates store
  loginSuccess: (response: AuthResponse) => {
    const { login } = useAuthStore.getState();

    // Backend may set HttpOnly cookies, but also returns tokens in body for fallback.
    const user = (response as any).user || (response as any).data || null;
    const accessToken = (response as any).access_token || (response as any).accessToken || null;
    const refreshToken = (response as any).refresh_token || (response as any).refreshToken || null;

    if (typeof window !== 'undefined') {
      // Note: We rely on Zustand persist middleware to handle storage.
      // Manual storage is removed to prevent inconsistencies.
    }

    // Dispatch auth event to notify other parts of the app
    if (typeof window !== 'undefined') {
      window.dispatchEvent(new CustomEvent('auth:login', {
        detail: { user }
      }));
    }

    // Update store (store tokens as well for compatibility)
    login(user, accessToken || null, refreshToken || null);

    console.log('✅ Login successful for user:', user?.email ?? 'unknown');
  },

  // Alternative login method for compatibility
  loginWithResponse: async (response: AuthResponse) => {
    authActions.loginSuccess(response);
  },

  // Logout function
  logout: () => {
    const { logout } = useAuthStore.getState();
    logout();

    // Attempt server-side logout to clear HttpOnly cookies, then dispatch event and redirect
    if (typeof window !== 'undefined') {
      (async () => {
        try {
          const { API_CONFIG } = await import('@/lib/constants');
          await fetch(`${API_CONFIG.BASE_URL}/auth/logout`, { method: 'POST', credentials: 'include' });
        } catch (e) {
          // ignore
        }
        window.dispatchEvent(new CustomEvent('auth:logout'));
        window.location.href = '/auth/login';
      })();
    }
  },

  // Alternative logout method for compatibility
  logoutAndRedirect: (redirectPath?: string) => {
    authActions.logout();
    if (redirectPath) {
      window.location.href = redirectPath;
    }
  },

  // Initialize auth function - uses direct store method
  initializeAuth: async () => {
    try {
      const { initializeAuth } = useAuthStore.getState();
      await initializeAuth();
    } catch (error) {
      console.error('Auth initialization failed:', error);
    }
  },
};

// Listen for auth events (only in browser environment)
if (typeof window !== 'undefined') {
  window.addEventListener('auth:login', (event: any) => {
    console.log('🔔 Auth event received: login', event.detail);
  });

  window.addEventListener('auth:logout', () => {
    console.log('🔔 Auth event received: logout');
  });
}