/**
 * Test case สำหรับตรวจสอบปัญหาลูปการเรียก initializeAuth
 * 
 * ทดสอบ:
 * 1. ไม่มีการเรียก initializeAuth ซ้ำซ้อน
 * 2. Guard flags ทำงานถูกต้อง
 * 3. Debouncing ป้องกันการเรียกซ้ำ
 * 4. ระบบทำงานได้ปกติ
 */

import { renderHook, act, waitFor } from '@testing-library/react';
import { useAuthState, useAuth } from '@/hooks/use-auth-state';
import { authActions } from '@/stores/auth-actions';
import { useAuthStore } from '@/stores/auth-store';
import { jest } from '@jest/globals';

// Mock global objects
global.localStorage = {
  getItem: jest.fn(),
  setItem: jest.fn(),
  removeItem: jest.fn(),
  clear: jest.fn(),
} as any;

global.fetch = jest.fn();
global.window = {
  dispatchEvent: jest.fn(),
  location: { pathname: '/' },
  addEventListener: jest.fn(),
  removeEventListener: jest.fn(),
} as any;

describe('Auth Initialization Loop Fix', () => {
  let consoleSpy: jest.SpyInstance;

  beforeEach(() => {
    jest.clearAllMocks();
    consoleSpy = jest.spyOn(console, 'log').mockImplementation(() => {});
    
    // Reset store state
    (useAuthStore.getState() as any).user = null;
    (useAuthStore.getState() as any).isAuthenticated = false;
    (useAuthStore.getState() as any).isLoading = true;
    (useAuthStore.getState() as any).isInitialized = false;
    
    // Reset guard flags
    (useAuthState as any)._isInitializing = false;
    (useAuthState as any)._lastInitCall = 0;
    (authActions as any)._lastInitCall = 0;
    (globalThis as any).__auth_initializing = false;
  });

  afterEach(() => {
    consoleSpy.mockRestore();
  });

  describe('Debouncing Tests', () => {
    test('should prevent rapid successive calls to authActions.initializeAuth', async () => {
      // Arrange
      const mockFetch = global.fetch as jest.MockedFunction<typeof fetch>;
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ email: 'test@example.com', id: 1 })
      } as Response);
      
      global.localStorage.getItem.mockImplementation((key: string) => {
        if (key === 'access_token') return 'mock-token';
        return null;
      });

      // Act - Call initializeAuth multiple times rapidly
      const promises = [
        authActions.initializeAuth(),
        authActions.initializeAuth(),
        authActions.initializeAuth(),
        authActions.initializeAuth(),
        authActions.initializeAuth()
      ];

      await Promise.all(promises);

      // Assert - Should only execute once due to debouncing
      expect(mockFetch).toHaveBeenCalledTimes(1);
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/auth/me'),
        expect.objectContaining({
          headers: { 'Authorization': 'Bearer mock-token' }
        })
      );
    });

    test('should prevent rapid successive calls to useAuthState hook', async () => {
      // Arrange
      const mockFetch = global.fetch as jest.MockedFunction<typeof fetch>;
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ email: 'test@example.com', id: 1 })
      } as Response);
      
      global.localStorage.getItem.mockImplementation((key: string) => {
        if (key === 'access_token') return 'mock-token';
        return null;
      });

      // Act - Render hook multiple times rapidly
      const { result, rerender } = renderHook(() => useAuthState());
      
      // Simulate rapid re-renders
      for (let i = 0; i < 5; i++) {
        rerender();
      }

      // Wait for async operations to complete
      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      }, { timeout: 2000 });

      // Assert - Should handle multiple renders without multiple initialization calls
      expect(mockFetch).toHaveBeenCalledTimes(1);
    });
  });

  describe('Guard Flags Tests', () => {
    test('should prevent concurrent initialization', async () => {
      // Arrange
      const mockFetch = global.fetch as jest.MockedFunction<typeof fetch>;
      let resolveCount = 0;
      
      mockFetch.mockImplementation(() => {
        return new Promise(resolve => {
          setTimeout(() => {
            resolveCount++;
            resolve({
              ok: true,
              json: async () => ({ 
                email: `test${resolveCount}@example.com`, 
                id: resolveCount 
              })
            } as Response);
          }, 100); // Simulate slow network
        });
      });
      
      global.localStorage.getItem.mockImplementation((key: string) => {
        if (key === 'access_token') return 'mock-token';
        return null;
      });

      // Set global flag to simulate ongoing initialization
      (globalThis as any).__auth_initializing = true;

      // Act
      await authActions.initializeAuth();

      // Assert - Should not make any calls when already initializing
      expect(mockFetch).not.toHaveBeenCalled();
      expect(resolveCount).toBe(0);
    });

    test('should skip initialization if already initialized with user', async () => {
      // Arrange - Set pre-existing authenticated state
      useAuthStore.setState({
        user: { email: 'existing@example.com', id: 1 } as any,
        isAuthenticated: true,
        isInitialized: true
      });

      const mockFetch = global.fetch as jest.MockedFunction<typeof fetch>;

      // Act
      await authActions.initializeAuth();

      // Assert - Should skip initialization
      expect(mockFetch).not.toHaveBeenCalled();
    });
  });

  describe('Integration Tests', () => {
    test('should complete initialization successfully without loops', async () => {
      // Arrange
      const mockFetch = global.fetch as jest.MockedFunction<typeof fetch>;
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ email: 'admin@insightflow.com', id: 1, role: 'admin' })
      } as Response);
      
      global.localStorage.getItem.mockImplementation((key: string) => {
        if (key === 'access_token') return 'valid-token';
        return null;
      });

      // Act
      const { result } = renderHook(() => useAuthState());

      // Wait for initialization to complete
      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      }, { timeout: 3000 });

      // Assert
      expect(result.current.isAuthenticated).toBe(true);
      expect(result.current.user?.email).toBe('admin@insightflow.com');
      expect(result.current.isLoading).toBe(false);
      expect(mockFetch).toHaveBeenCalledTimes(1);
    });

    test('should handle initialization failure gracefully', async () => {
      // Arrange
      const mockFetch = global.fetch as jest.MockedFunction<typeof fetch>;
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 401,
        statusText: 'Unauthorized'
      } as Response);
      
      global.localStorage.getItem.mockImplementation((key: string) => {
        if (key === 'access_token') return 'invalid-token';
        return null;
      });

      // Act
      const { result } = renderHook(() => useAuthState());

      // Wait for initialization to complete
      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      }, { timeout: 3000 });

      // Assert - Should handle 401 gracefully
      expect(result.current.isAuthenticated).toBe(false);
      expect(result.current.user).toBe(null);
      expect(result.current.isLoading).toBe(false);
      expect(mockFetch).toHaveBeenCalledTimes(1);
    });
  });

  describe('Performance Tests', () => {
    test('should initialize within reasonable time frame', async () => {
      // Arrange
      const startTime = Date.now();
      const mockFetch = global.fetch as jest.MockedFunction<typeof fetch>;
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ email: 'test@example.com', id: 1 })
      } as Response);
      
      global.localStorage.getItem.mockImplementation((key: string) => {
        if (key === 'access_token') return 'mock-token';
        return null;
      });

      // Act
      const { result } = renderHook(() => useAuthState());

      await waitFor(() => {
        return !result.current.isLoading;
      }, { timeout: 5000 });

      const endTime = Date.now();
      const duration = endTime - startTime;

      // Assert - Should complete within 2 seconds (generous timeout for CI)
      expect(duration).toBeLessThan(2000);
      expect(result.current.isLoading).toBe(false);
    });
  });

  describe('Logging Tests', () => {
    test('should log initialization process correctly', async () => {
      // Arrange
      const mockFetch = global.fetch as jest.MockedFunction<typeof fetch>;
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ email: 'test@example.com', id: 1 })
      } as Response);
      
      global.localStorage.getItem.mockImplementation((key: string) => {
        if (key === 'access_token') return 'mock-token';
        return null;
      });

      // Act
      await authActions.initializeAuth();

      // Assert - Should have logged initialization steps
      const logMessages = consoleSpy.mock.calls.map(call => call[0]);
      
      expect(logMessages).toEqual(expect.arrayContaining([
        expect.stringContaining('authActions: initializeAuth called'),
        expect.stringContaining('AuthStore: initializeAuth called'),
        expect.stringContaining('AuthStore: Starting initialization'),
        expect.stringContaining('AuthStore: /auth/me response received'),
        expect.stringContaining('AuthStore: Completed initialization'),
        expect.stringContaining('AuthStore: End')
      ]));
    });
  });
});

/**
 * Manual Test Instructions:
 * 
 * 1. เปิด browser developer console
 * 2. ล็อกอินด้วย admin@insightflow.com
 * 3. ดู console logs เพื่อตรวจสอบ:
 *    - ไม่มีการเรียก initializeAuth ซ้ำเกิน 1-2 ครั้ง
 *    - มี call ID แตกต่างกันสำหรับแต่ละครั้ง
 *    - ไม่มี infinite loop
 * 
 * 4. ทดสอบ scenarios:
 *    - ล็อกอินใหม่
 *    - Refresh หน้า
 *    - เปลี่ยนหน้าไปกลับ
 *    - เปิด developer tools และดู network tab
 */