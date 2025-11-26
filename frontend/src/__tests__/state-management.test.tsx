// ===========================================
// State Management Tests
// ===========================================

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { renderHook, act, waitFor } from '@testing-library/react';
import React from 'react';

// Import stores and hooks for testing
import { useAuthStore } from '@/stores/auth-store';
import { useAppStore } from '@/stores/app-store';
import { useThemeStore } from '@/stores/theme-store';
import { useNotificationStore } from '@/stores/notification-store';

import { useAuth, useAuthState } from '@/hooks/use-auth-state';
import { useAppState, useLoading, useModal } from '@/hooks/use-app-state';
import { useTheme, useDarkMode } from '@/hooks/use-theme';
import { useNotifications, useUnreadNotifications } from '@/hooks/use-notifications';
import { useAppIntegration } from '@/hooks/use-integration';

// Test wrapper (no React Query dependency)
const createWrapper = () => {
  return ({ children }: { children: React.ReactNode }) => (
    <>{children}</>
  );
};

// ===========================================
// Authentication Store Tests
// ===========================================

describe('Authentication Store', () => {
  beforeEach(() => {
    useAuthStore.setState({
      user: null,
      isAuthenticated: false,
      isLoading: false,
      accessToken: null,
      refreshToken: null,
    });
  });

  afterEach(() => {
    localStorage.clear();
  });

  it('should initialize with default state', () => {
    const { result } = renderHook(() => useAuthStore());
    
    expect(result.current.isAuthenticated).toBe(false);
    expect(result.current.user).toBe(null);
    expect(result.current.isLoading).toBe(false);
    expect(result.current.accessToken).toBe(null);
  });

  it('should set user and mark as authenticated', () => {
    const mockUser = {
      id: '1',
      username: 'testuser',
      email: 'test@example.com',
      role: 'user',
      is_active: true,
      created_at: new Date(),
      updated_at: new Date(),
    };

    act(() => {
      useAuthStore.getState().setUser(mockUser);
      useAuthStore.getState().setTokens('access-token', 'refresh-token');
    });

    expect(useAuthStore.getState().isAuthenticated).toBe(true);
    expect(useAuthStore.getState().user).toEqual(mockUser);
    expect(useAuthStore.getState().accessToken).toBe('access-token');
  });

  it('should logout and clear state', () => {
    const mockUser = { id: '1', username: 'testuser', email: 'test@example.com', role: 'user', is_active: true, created_at: new Date(), updated_at: new Date() };
    
    act(() => {
      useAuthStore.getState().setUser(mockUser);
      useAuthStore.getState().setTokens('access-token', 'refresh-token');
    });

    act(() => {
      useAuthStore.getState().logout();
    });

    expect(useAuthStore.getState().isAuthenticated).toBe(false);
    expect(useAuthStore.getState().user).toBe(null);
    expect(useAuthStore.getState().accessToken).toBe(null);
  });
});

// ===========================================
// App Store Tests
// ===========================================

describe('App Store', () => {
  beforeEach(() => {
    useAppStore.setState({
      isLoading: false,
      isSideNavOpen: true,
      isFullscreen: false,
      isDarkMode: false,
      breadcrumbs: [],
      alerts: [],
      modals: [],
      search: { query: '', filters: {}, isActive: false, isSearching: false },
      forms: {},
      currentProjectId: null,
      userPreferences: {},
      notifications: [],
      toasts: [],
    });
  });

  it('should initialize with default state', () => {
    const { result } = renderHook(() => useAppStore());
    
    expect(result.current.isLoading).toBe(false);
    expect(result.current.isSideNavOpen).toBe(true);
    expect(result.current.isDarkMode).toBe(false);
    expect(result.current.breadcrumbs).toHaveLength(0);
    expect(result.current.alerts).toHaveLength(0);
  });

  it('should toggle side navigation', () => {
    act(() => {
      useAppStore.getState().toggleSideNav();
    });

    expect(useAppStore.getState().isSideNavOpen).toBe(false);

    act(() => {
      useAppStore.getState().toggleSideNav();
    });

    expect(useAppStore.getState().isSideNavOpen).toBe(true);
  });

  it('should add and remove alerts', () => {
    act(() => {
      useAppStore.getState().addAlert({
        id: '1',
        type: 'success',
        message: 'Test message',
        timestamp: new Date(),
      });
    });

    expect(useAppStore.getState().alerts).toHaveLength(1);

    act(() => {
      useAppStore.getState().removeAlert('1');
    });

    expect(useAppStore.getState().alerts).toHaveLength(0);
  });

  it('should show and hide modals', () => {
    act(() => {
      useAppStore.getState().showModal('test-modal', {
        type: 'confirm',
        title: 'Test Modal',
        message: 'Test message',
      });
    });

    expect(useAppStore.getState().modals).toHaveLength(1);
    expect(useAppStore.getState().modals[0].id).toBe('test-modal');

    act(() => {
      useAppStore.getState().hideModal('test-modal');
    });

    expect(useAppStore.getState().modals).toHaveLength(0);
  });

  it('should update search', () => {
    act(() => {
      useAppStore.getState().setSearch({
        query: 'test search',
        filters: { type: 'project' },
        isActive: true,
        isSearching: false,
      });
    });

    expect(useAppStore.getState().search.query).toBe('test search');
    expect(useAppStore.getState().search.isActive).toBe(true);
  });
});

// ===========================================
// Theme Store Tests
// ===========================================

describe('Theme Store', () => {
  beforeEach(() => {
    useThemeStore.setState({
      currentTheme: 'light',
      systemPrefersDark: false,
      isSystemMode: false,
      primaryColor: '#3b82f6',
      availableThemes: ['light', 'dark', 'system'],
      colorScheme: 'light',
      nextTheme: 'dark',
    });
  });

  it('should initialize with default state', () => {
    const { result } = renderHook(() => useThemeStore());
    
    expect(result.current.currentTheme).toBe('light');
    expect(result.current.systemPrefersDark).toBe(false);
    expect(result.current.isSystemMode).toBe(false);
    expect(result.current.primaryColor).toBe('#3b82f6');
  });

  it('should toggle between light and dark theme', () => {
    act(() => {
      useThemeStore.getState().toggleTheme();
    });

    expect(useThemeStore.getState().currentTheme).toBe('dark');
    expect(useThemeStore.getState().isSystemMode).toBe(false);

    act(() => {
      useThemeStore.getState().toggleTheme();
    });

    expect(useThemeStore.getState().currentTheme).toBe('light');
  });

  it('should enable and disable system theme', () => {
    act(() => {
      useThemeStore.getState().enableAutoTheme();
    });

    expect(useThemeStore.getState().isSystemMode).toBe(true);

    act(() => {
      useThemeStore.getState().disableAutoTheme();
    });

    expect(useThemeStore.getState().isSystemMode).toBe(false);
  });

  it('should set primary color', () => {
    act(() => {
      useThemeStore.getState().setPrimaryColor('#ef4444');
    });

    expect(useThemeStore.getState().primaryColor).toBe('#ef4444');
  });

  it('should reset theme to default', () => {
    act(() => {
      useThemeStore.getState().setTheme('dark');
      useThemeStore.getState().setPrimaryColor('#ef4444');
    });

    expect(useThemeStore.getState().currentTheme).toBe('dark');
    expect(useThemeStore.getState().primaryColor).toBe('#ef4444');

    act(() => {
      useThemeStore.getState().resetTheme();
    });

    expect(useThemeStore.getState().currentTheme).toBe('light');
    expect(useThemeStore.getState().primaryColor).toBe('#3b82f6');
  });
});

// ===========================================
// Notifications Store Tests
// ===========================================

describe('Notifications Store', () => {
  beforeEach(() => {
    useNotificationStore.setState({
      notifications: [],
      isLoading: false,
      isConnected: false,
      filters: {
        type: 'all',
        priority: 'all',
        readStatus: 'all',
        search: '',
        dateRange: undefined,
      },
    });
  });

  it('should initialize with default state', () => {
    const { result } = renderHook(() => useNotificationStore());
    
    expect(result.current.notifications).toHaveLength(0);
    expect(result.current.isLoading).toBe(false);
    expect(result.current.isConnected).toBe(false);
    expect(result.current.filters.type).toBe('all');
  });

  it('should add and remove notifications', () => {
    const mockNotification = {
      id: '1',
      userId: 'test-user',
      title: 'Test Notification',
      message: 'Test message',
      type: 'system' as const,
      priority: 'medium' as const,
      read: false,
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
    };

    act(() => {
      useNotificationStore.getState().addNotification(mockNotification);
    });

    expect(useNotificationStore.getState().notifications).toHaveLength(1);

    act(() => {
      useNotificationStore.getState().removeNotification('1');
    });

    expect(useNotificationStore.getState().notifications).toHaveLength(0);
  });

  it('should mark notifications as read', () => {
    const mockNotification = {
      id: '1',
      userId: 'test-user',
      title: 'Test Notification',
      message: 'Test message',
      type: 'system' as const,
      priority: 'medium' as const,
      read: false,
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
    };

    act(() => {
      useNotificationStore.getState().addNotification(mockNotification);
    });

    act(() => {
      useNotificationStore.getState().markAsRead('1');
    });

    expect(useNotificationStore.getState().notifications[0].read).toBe(true);
  });

  it('should mark all notifications as read', () => {
    const mockNotifications = [
      {
        id: '1',
        userId: 'test-user',
        title: 'Test 1',
        message: 'Message 1',
        type: 'system' as const,
        priority: 'medium' as const,
        read: false,
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString(),
      },
      {
        id: '2',
        userId: 'test-user',
        title: 'Test 2',
        message: 'Message 2',
        type: 'system' as const,
        priority: 'medium' as const,
        read: false,
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString(),
      },
    ];

    act(() => {
      mockNotifications.forEach(notification => {
        useNotificationStore.getState().addNotification(notification);
      });
    });

    act(() => {
      useNotificationStore.getState().markAllAsRead();
    });

    expect(useNotificationStore.getState().notifications.every(n => n.read)).toBe(true);
  });

  it('should clear notifications', () => {
    const mockNotification = {
      id: '1',
      userId: 'test-user',
      title: 'Test Notification',
      message: 'Test message',
      type: 'system' as const,
      priority: 'medium' as const,
      read: false,
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
    };

    act(() => {
      useNotificationStore.getState().addNotification(mockNotification);
    });

    expect(useNotificationStore.getState().notifications).toHaveLength(1);

    act(() => {
      useNotificationStore.getState().clearNotifications();
    });

    expect(useNotificationStore.getState().notifications).toHaveLength(0);
  });

  it('should update filters', () => {
    act(() => {
      useNotificationStore.getState().updateFilters({
        type: 'task_assigned',
        priority: 'high',
      });
    });

    expect(useNotificationStore.getState().filters.type).toBe('task_assigned');
    expect(useNotificationStore.getState().filters.priority).toBe('high');
  });
});

// ===========================================
// Hook Integration Tests
// ===========================================

describe('Custom Hooks', () => {
  const wrapper = createWrapper();

  it('useAuth hook should work correctly', async () => {
    const { result } = renderHook(() => useAuth(), { wrapper });

    expect(result.current.isAuthenticated).toBe(false);
    expect(result.current.isLoading).toBe(false);
    expect(result.current.user).toBe(null);
  });

  it('useTheme hook should work correctly', () => {
    const { result } = renderHook(() => useTheme(), { wrapper });

    expect(result.current.currentTheme).toBe('light');
    expect(result.current.isDarkMode).toBe(false);
    expect(result.current.isLightMode).toBe(true);
    expect(result.current.isSystemMode).toBe(false);
  });

  it('useAppState hook should work correctly', () => {
    const { result } = renderHook(() => useAppState(), { wrapper });

    expect(result.current.isLoading).toBe(false);
    expect(result.current.isSideNavOpen).toBe(true);
    expect(result.current.isDarkMode).toBe(false);
    expect(result.current.breadcrumbs).toHaveLength(0);
    expect(result.current.alerts).toHaveLength(0);
  });

  it('useNotifications hook should work correctly', () => {
    const { result } = renderHook(() => useNotifications(), { wrapper });

    expect(result.current.notifications).toHaveLength(0);
    expect(result.current.unreadCount).toBe(0);
    expect(result.current.isLoading).toBe(false);
    expect(result.current.isConnected).toBe(false);
  });

  it('useLoading hook should work correctly', async () => {
    const { result } = renderHook(() => useLoading(), { wrapper });

    expect(result.current.isLoading).toBe(false);

    act(() => {
      result.current.startLoading('Loading...');
    });

    expect(result.current.isLoading).toBe(true);

    act(() => {
      result.current.stopLoading();
    });

    expect(result.current.isLoading).toBe(false);

    const mockAsyncFunction = vi.fn().mockResolvedValue('success');

    await act(async () => {
      const result = await result.current.withLoading(mockAsyncFunction);
      expect(result).toBe('success');
      expect(mockAsyncFunction).toHaveBeenCalledTimes(1);
    });
  });
});

// ===========================================
// State Management Integration Tests
// ===========================================

describe('State Management Integration', () => {
  const wrapper = createWrapper();

  it('should persist auth state in localStorage', async () => {
    localStorage.setItem.mockClear?.(); // Clear any previous calls
    
    const { result } = renderHook(() => useAuth(), { wrapper });

    // Mock localStorage
    const localStorageMock = {
      getItem: vi.fn(),
      setItem: vi.fn(),
      removeItem: vi.fn(),
    };
    global.localStorage = localStorageMock as any;

    act(() => {
      useAuthStore.getState().setTokens('test-token', 'refresh-token');
    });

    expect(localStorageMock.setItem).toHaveBeenCalledWith('insight-flow-auth', expect.any(String));
  });

  it('should persist theme preference in localStorage', () => {
    // Mock localStorage
    const localStorageMock = {
      getItem: vi.fn(),
      setItem: vi.fn(),
      removeItem: vi.fn(),
    };
    global.localStorage = localStorageMock as any;

    act(() => {
      useThemeStore.getState().setTheme('dark');
    });

    expect(localStorageMock.setItem).toHaveBeenCalledWith('insight-flow-theme', expect.any(String));
  });

  it('should sync theme with document className', () => {
    // Mock document
    const mockDocument = {
      documentElement: {
        className: '',
        setAttribute: vi.fn(),
        getAttribute: vi.fn(),
      },
    };
    global.document = mockDocument as any;

    act(() => {
      useThemeStore.getState().setTheme('dark');
    });

    expect(mockDocument.documentElement.className).toContain('theme-dark');
  });

  it('should handle concurrent state updates correctly', () => {
    // Test multiple concurrent updates
    act(() => {
      useAuthStore.getState().setUser({ id: '1', username: 'test', email: 'test@example.com', role: 'user', is_active: true, created_at: new Date(), updated_at: new Date() });
      useAppStore.getState().addAlert({ id: '1', type: 'info', message: 'Test', timestamp: new Date() });
      useThemeStore.getState().setTheme('dark');
    });

    expect(useAuthStore.getState().isAuthenticated).toBe(true);
    expect(useAppStore.getState().alerts).toHaveLength(1);
    expect(useThemeStore.getState().currentTheme).toBe('dark');
  });

  it('should handle store reset correctly', () => {
    // Set up some state
    act(() => {
      useAuthStore.getState().setUser({ id: '1', username: 'test', email: 'test@example.com', role: 'user', is_active: true, created_at: new Date(), updated_at: new Date() });
      useAuthStore.getState().setTokens('token', 'refresh');
      useAppStore.getState().addAlert({ id: '1', type: 'info', message: 'Test', timestamp: new Date() });
      useNotificationStore.getState().addNotification({
        id: '1',
        userId: 'test-user',
        title: 'Test',
        message: 'Message',
        type: 'system',
        priority: 'medium',
        read: false,
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString(),
      });
    });

    // Reset all stores
    act(() => {
      useAuthStore.getState().logout();
      useAppStore.getState().resetAppState();
      useNotificationStore.getState().clearNotifications();
      useThemeStore.getState().resetTheme();
    });

    // Verify all stores are reset
    expect(useAuthStore.getState().isAuthenticated).toBe(false);
    expect(useAuthStore.getState().user).toBe(null);
    expect(useAppStore.getState().alerts).toHaveLength(0);
    expect(useNotificationStore.getState().notifications).toHaveLength(0);
    expect(useThemeStore.getState().currentTheme).toBe('light');
  });
});

// ===========================================
// Error Handling Tests
// ===========================================

describe('Error Handling', () => {
  it('should handle invalid localStorage operations', () => {
    // Mock localStorage to throw errors
    const localStorageMock = {
      getItem: () => { throw new Error('Storage quota exceeded'); },
      setItem: () => { throw new Error('Storage full'); },
    };
    global.localStorage = localStorageMock as any;

    expect(() => {
      useAuthStore.getState().setTokens('token', 'refresh');
    }).not.toThrow(); // Should not throw, just log warning

    expect(() => {
      useThemeStore.getState().setTheme('dark');
    }).not.toThrow();
  });

  it('should handle invalid theme colors', () => {
    expect(() => {
      useThemeStore.getState().setPrimaryColor('invalid-color');
    }).not.toThrow();

    expect(useThemeStore.getState().primaryColor).toBe('invalid-color'); // Should store whatever is passed
  });

  it('should handle missing notification properties', () => {
    expect(() => {
      useNotificationStore.getState().addNotification({
        userId: 'test-user',
        title: '',
        message: '',
        type: 'system',
        priority: 'medium',
        read: false,
      });
    }).not.toThrow();

    expect(useNotificationStore.getState().notifications).toHaveLength(1);
  });
});

// ===========================================
// Performance Tests
// ===========================================

describe('Performance', () => {
  it('should handle large numbers of notifications', () => {
    const start = performance.now();
    
    act(() => {
      for (let i = 0; i < 1000; i++) {
        useNotificationStore.getState().addNotification({
          userId: 'test-user',
          title: `Notification ${i}`,
          message: `Message ${i}`,
          type: 'system',
          priority: 'medium',
          read: false,
        });
      }
    });

    const end = performance.now();
    expect(end - start).toBeLessThan(1000); // Should complete within 1 second
    expect(useNotificationStore.getState().notifications).toHaveLength(1000);
  });

  it('should handle rapid state updates', () => {
    const start = performance.now();
    
    act(() => {
      for (let i = 0; i < 100; i++) {
        useAppStore.getState().toggleSideNav();
      }
    });

    const end = performance.now();
    expect(end - start).toBeLessThan(100); // Should complete within 100ms
  });
});

// ===========================================
// Utility Test Helpers
// ===========================================

/**
 * Test helper to mock API responses
 */
export const mockApiResponse = (data: any, delay = 0) => {
  return new Promise(resolve => {
    setTimeout(() => resolve(data), delay);
  });
};

/**
 * Test helper to wait for store updates
 */
export const waitForStoreUpdate = (store: any, predicate: (state: any) => boolean) => {
  return waitFor(() => {
    expect(predicate(store.getState())).toBe(true);
  });
};

/**
 * Test helper to reset all stores to initial state
 */
export const resetAllStores = () => {
  act(() => {
    useAuthStore.getState().logout();
    useAppStore.getState().resetAppState();
    useNotificationStore.getState().clearNotifications();
    useThemeStore.getState().resetTheme();
  });
};