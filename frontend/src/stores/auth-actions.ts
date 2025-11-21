// ===========================================
// Auth Actions (Separated to avoid circular dependency)
// ===========================================

import { useAuthStore } from './auth-store';
import { AuthResponse } from '@/types';

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
      if (user) {
        try { localStorage.setItem('user', JSON.stringify(user)); } catch (e) { console.warn('Failed to persist user to localStorage', e); }
      }
      // Fallback: persist tokens to localStorage in development if backend provides them
      if (accessToken) {
        localStorage.setItem('access_token', accessToken);
        localStorage.setItem('accessToken', accessToken);
      }
      if (refreshToken) {
        localStorage.setItem('refresh_token', refreshToken);
        localStorage.setItem('refreshToken', refreshToken);
      }
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

  // Initialize auth function - uses direct store method with enhanced debouncing
  initializeAuth: async () => {
    // 🚫 Prevent rapid successive calls with debounce
    const now = Date.now();
    if ((authActions as any)._lastInitCall && (now - (authActions as any)._lastInitCall) < 1000) {
      console.log(`⏱️ authActions: Debouncing rapid calls, last call was`, now - (authActions as any)._lastInitCall, 'ms ago');
      return;
    }
    (authActions as any)._lastInitCall = now;

    const callId = `actions_init_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    console.log(`🔥 authActions: initializeAuth called [${callId}] at`, new Date().toISOString());
    const { initializeAuth } = useAuthStore.getState();
    console.log(`🔥 authActions: calling store.initializeAuth [${callId}], call stack:`);
    console.trace();
    return initializeAuth();
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