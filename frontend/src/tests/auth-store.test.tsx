/**
 * Unit tests for auth-store.
 */
import { describe, it, expect, vi, beforeEach, afterEach, type Mock } from "vitest";
import { act } from "@testing-library/react";
import type { User } from "@/types";

// Mock localStorage
const localStorageMock = (() => {
  let store: Record<string, string> = {};
  return {
    getItem: vi.fn((key: string) => store[key] || null),
    setItem: vi.fn((key: string, value: string) => {
      store[key] = value;
    }),
    removeItem: vi.fn((key: string) => {
      delete store[key];
    }),
    clear: vi.fn(() => {
      store = {};
    }),
  };
})();

const sessionStorageMock = (() => {
  let store: Record<string, string> = {};
  return {
    getItem: vi.fn((key: string) => store[key] || null),
    setItem: vi.fn((key: string, value: string) => {
      store[key] = value;
    }),
    removeItem: vi.fn((key: string) => {
      delete store[key];
    }),
    clear: vi.fn(() => {
      store = {};
    }),
  };
})();

Object.defineProperty(window, "localStorage", { value: localStorageMock });
Object.defineProperty(window, "sessionStorage", { value: sessionStorageMock });

// Mock API endpoints
vi.mock("@/lib/api-endpoints", () => ({
  authApi: {
    logout: vi.fn().mockResolvedValue(undefined),
    getCurrentUser: vi.fn(),
  },
  usersApi: {
    getCurrentUser: vi.fn(),
    updateCurrentUser: vi.fn(),
  },
}));

// Mock API client
vi.mock("@/lib/api-client", () => ({
  apiClient: {
    get: vi.fn(),
  },
  registerLogoutHandler: vi.fn(),
  isAxiosError: vi.fn((err: any) => Boolean(err && (err.isAxiosError || err.response))),
}));

describe("auth-store", () => {
  beforeEach(async () => {
    vi.clearAllMocks();
    localStorageMock.clear();
    sessionStorageMock.clear();
    vi.useFakeTimers();
    vi.setSystemTime(new Date("2024-01-01"));
    vi.resetModules();
    window.history.pushState({}, "", "/dashboard");
    
    // Ensure store is clean even if resetModules fails to create a fresh one (e.g. if cached somewhere)
    // Note: This relies on the fact that if we get a recycled store, we clean it. 
    // If we get a new store, it's clean by default.
    const { useAuthStore } = await import("@/stores/auth-store");
    act(() => {
        useAuthStore.setState({
            user: null,
            isAuthenticated: false,
            isLoading: true,
            isInitialized: false,
            lastActivity: 0,
            rememberMe: false
        }); // merge
    });
  });

  afterEach(() => {
    vi.clearAllMocks();
    vi.useRealTimers();
  });

  describe("initial state", () => {
    it("should have correct initial state", async () => {
      const { useAuthStore } = await import("@/stores/auth-store");
      const state = useAuthStore.getState();

      expect(state.isAuthenticated).toBe(false);
      expect(state.user).toBe(null);
      expect(state.isLoading).toBe(true); // Initially loading
      expect(state.isInitialized).toBe(false);
    });
  });

  describe("actions", () => {
    it("setUser should set user and authenticate", async () => {
      const { useAuthStore } = await import("@/stores/auth-store");
      const mockUser = { id: "1", email: "test@example.com" } as User;

      act(() => {
        useAuthStore.getState().setUser(mockUser);
      });

      const state = useAuthStore.getState();
      expect(state.user).toEqual(mockUser);
      expect(state.isAuthenticated).toBe(true);
    });

    it("setUser should handle null user", async () => {
      const { useAuthStore } = await import("@/stores/auth-store");
      
      act(() => {
        useAuthStore.getState().setUser(null);
      });

      const state = useAuthStore.getState();
      expect(state.user).toBe(null);
      expect(state.isAuthenticated).toBe(false);
    });

    it("login should set full auth state", async () => {
      const { useAuthStore } = await import("@/stores/auth-store");
      const mockUser = { id: "1", email: "test@example.com" } as User;

      act(() => {
        useAuthStore.getState().login(mockUser);
      });

      const state = useAuthStore.getState();
      expect(state.user).toEqual(mockUser);
      expect(state.isAuthenticated).toBe(true);
      expect(state.isLoading).toBe(false);
      expect(state.isInitialized).toBe(true);
    });

    it("login should persist auth state to sessionStorage unless remember me is selected", async () => {
      const { useAuthStore } = await import("@/stores/auth-store");
      const mockUser = { id: "1", email: "test@example.com" } as User;

      act(() => {
        useAuthStore.getState().login(mockUser);
      });

      expect(sessionStorageMock.setItem).toHaveBeenCalledWith(
        "insight-flow-auth",
        expect.any(String),
      );
      expect(localStorageMock.removeItem).toHaveBeenCalledWith("insight-flow-auth");
      expect(localStorageMock.setItem).not.toHaveBeenCalledWith(
        "insight-flow-auth",
        expect.any(String),
      );
    });

    it("login should persist auth state to localStorage when remember me is selected", async () => {
      const { useAuthStore } = await import("@/stores/auth-store");
      const mockUser = { id: "1", email: "test@example.com" } as User;

      act(() => {
        useAuthStore.getState().login(mockUser, { rememberMe: true });
      });

      expect(localStorageMock.setItem).toHaveBeenCalledWith(
        "insight-flow-auth",
        expect.any(String),
      );
      expect(sessionStorageMock.removeItem).toHaveBeenCalledWith("insight-flow-auth");
    });

    it("logout should clear state", async () => {
      const { useAuthStore } = await import("@/stores/auth-store");
      const mockUser = { id: "1", email: "test@example.com" } as User;
      
      act(() => {
        useAuthStore.getState().login(mockUser);
      });

      act(() => {
        useAuthStore.getState().logout();
      });

      const state = useAuthStore.getState();
      expect(state.user).toBe(null);
      expect(state.isAuthenticated).toBe(false);
      expect(state.isLoading).toBe(false);
      expect(state.isInitialized).toBe(false);
      expect(state.lastActivity).toBe(0);
      expect(localStorageMock.removeItem).toHaveBeenCalledWith("insight-flow-auth");
      expect(sessionStorageMock.removeItem).toHaveBeenCalledWith("insight-flow-auth");
      expect(localStorageMock.removeItem).toHaveBeenCalledWith("user");
      expect(localStorageMock.removeItem).toHaveBeenCalledWith("access_token");
      expect(localStorageMock.removeItem).toHaveBeenCalledWith("refresh_token");

      await act(async () => {
        await Promise.resolve();
      });

      expect(localStorageMock.getItem("insight-flow-auth")).toBe(null);
    });

    it("setLoading should update loading state", async () => {
      const { useAuthStore } = await import("@/stores/auth-store");
      
      act(() => {
        useAuthStore.getState().setLoading(false);
      });
      expect(useAuthStore.getState().isLoading).toBe(false);

      act(() => {
        useAuthStore.getState().setLoading(true);
      });
      expect(useAuthStore.getState().isLoading).toBe(true);
    });

    it("updateUserAvatar should update avatar url", async () => {
      const { useAuthStore } = await import("@/stores/auth-store");
      const mockUser = { id: "1", email: "test@example.com" } as User;
      
      act(() => {
        useAuthStore.getState().login(mockUser);
      });

      act(() => {
        useAuthStore.getState().updateUserAvatar("new-avatar.jpg");
      });

      expect(useAuthStore.getState().user?.avatar).toBe("new-avatar.jpg");
    });

    it("updateActivity should update lastActivity", async () => {
        const { useAuthStore } = await import("@/stores/auth-store");
        
        const initialActivity = useAuthStore.getState().lastActivity;
        
        vi.advanceTimersByTime(10000);
        
        act(() => {
            useAuthStore.getState().updateActivity();
        });

        expect(useAuthStore.getState().lastActivity).toBeGreaterThan(initialActivity);
    });
  });

  describe("initializeAuth", () => {
    it("should verify session if window is defined", async () => {
      const { useAuthStore } = await import("@/stores/auth-store");
      const { apiClient } = await import("@/lib/api-client");
      
      const mockUser = { id: "1", email: "test@example.com" } as User;
      (apiClient.get as Mock).mockResolvedValue({ data: mockUser });

      await act(async () => {
        await useAuthStore.getState().initializeAuth();
      });

      const state = useAuthStore.getState();
      expect(state.user).toEqual(mockUser);
      expect(state.isInitialized).toBe(true);
      expect(state.isAuthenticated).toBe(true);
      expect(apiClient.get).toHaveBeenCalledWith("/auth/me", {
        timeout: 8000,
        "axios-retry": { retries: 0 },
      });
    });

    it("should logout if session verification fails", async () => {
      const { useAuthStore } = await import("@/stores/auth-store");
      const { apiClient } = await import("@/lib/api-client");
      
      (apiClient.get as Mock).mockRejectedValue(new Error("Unauthorized"));

      await act(async () => {
        await useAuthStore.getState().initializeAuth();
      });

      const state = useAuthStore.getState();
      expect(state.user).toBe(null);
      expect(state.isAuthenticated).toBe(false);
      expect(state.isInitialized).toBe(true);
    });

    it("should clear persisted auth state on auth routes", async () => {
      window.history.pushState({}, "", "/auth/login");
      localStorageMock.setItem(
        "insight-flow-auth",
        JSON.stringify({
          state: {
            user: { email: "stale@example.com" },
            isAuthenticated: true,
            lastActivity: Date.now(),
            lastVerified: Date.now(),
          },
        }),
      );

      const { useAuthStore } = await import("@/stores/auth-store");
      const { apiClient } = await import("@/lib/api-client");

      act(() => {
        useAuthStore.setState({
          user: { email: "stale@example.com" } as User,
          isAuthenticated: true,
          isInitialized: false,
          isLoading: true,
          lastVerified: Date.now(),
        });
      });

      await act(async () => {
        await useAuthStore.getState().initializeAuth();
      });

      expect(apiClient.get).not.toHaveBeenCalled();
      expect(useAuthStore.getState().isAuthenticated).toBe(false);
      expect(useAuthStore.getState().user).toBe(null);
      expect(useAuthStore.getState().isInitialized).toBe(true);
      expect(localStorageMock.removeItem).toHaveBeenCalledWith("insight-flow-auth");

      await act(async () => {
        await Promise.resolve();
      });

      expect(localStorageMock.getItem("insight-flow-auth")).toBe(null);
    });

    it("should logout when fresh cached session is rejected by background verification", async () => {
      const { useAuthStore } = await import("@/stores/auth-store");
      const { apiClient } = await import("@/lib/api-client");
      const consoleLog = vi.spyOn(console, "log").mockImplementation(() => {});
      const consoleWarn = vi.spyOn(console, "warn").mockImplementation(() => {});
      const mockUser = { id: "1", email: "test@example.com" } as User;
      const authError = Object.assign(new Error("Forbidden"), {
        isAxiosError: true,
        response: { status: 403 },
      });

      (apiClient.get as Mock).mockRejectedValue(authError);
      act(() => {
        useAuthStore.setState({
          user: mockUser,
          isAuthenticated: true,
          isInitialized: false,
          isLoading: true,
          lastVerified: Date.now(),
        });
      });

      await act(async () => {
        await useAuthStore.getState().initializeAuth();
      });

      await act(async () => {
        await Promise.resolve();
        await Promise.resolve();
      });

      expect(useAuthStore.getState().isAuthenticated).toBe(false);
      expect(useAuthStore.getState().user).toBe(null);
      expect(consoleLog).toHaveBeenCalledWith(
        "✅ Using cached auth (verified",
        0,
        "seconds ago)",
      );
      expect(consoleWarn).toHaveBeenCalledWith("⚠️ Cached session invalid, logging out");
      consoleLog.mockRestore();
      consoleWarn.mockRestore();
    });
  });

  describe("checkAuthStatus", () => {
    it("should return false if not authenticated", async () => {
      const { useAuthStore } = await import("@/stores/auth-store");
      expect(useAuthStore.getState().checkAuthStatus()).toBe(false);
    });

    it("should logout if session expired (30 days)", async () => {
      const { useAuthStore } = await import("@/stores/auth-store");
      const mockUser = { id: "1", email: "test@example.com" } as User;
      
      act(() => {
        useAuthStore.getState().login(mockUser);
        // Manually set old activity
        useAuthStore.setState({ lastActivity: Date.now() - (31 * 24 * 60 * 60 * 1000) });
      });

      const isActive = useAuthStore.getState().checkAuthStatus();
      expect(isActive).toBe(false);
      expect(useAuthStore.getState().isAuthenticated).toBe(false);
    });
    
    it("should refresh activity if active", async () => {
      const { useAuthStore } = await import("@/stores/auth-store");
      const mockUser = { id: "1", email: "test@example.com" } as User;
      
      act(() => {
        useAuthStore.getState().login(mockUser);
      });
      
      vi.advanceTimersByTime(1000);

      const isActive = useAuthStore.getState().checkAuthStatus();
      expect(isActive).toBe(true);
    });
  });

  describe("async actions", () => {
      it("fetchUserProfile calls api and sets user", async () => {
          const { useAuthStore } = await import("@/stores/auth-store");
          const { usersApi } = await import("@/lib/api-endpoints");
          const mockUser = { id: "1", email: "test@example.com" } as User;
          
          (usersApi.getCurrentUser as Mock).mockResolvedValue(mockUser);

          await act(async () => {
              await useAuthStore.getState().fetchUserProfile();
          });

          expect(useAuthStore.getState().user).toEqual(mockUser);
      });

      it("updateUserProfile calls api and updates user", async () => {
          const { useAuthStore } = await import("@/stores/auth-store");
          const { usersApi } = await import("@/lib/api-endpoints");
          const initialUser = { id: "1", email: "old@example.com" } as User;
          const updateData = { firstName: "New" };
          const updatedUser = { ...initialUser, ...updateData };
          
          act(() => {
              useAuthStore.getState().setUser(initialUser);
          });
          
          (usersApi.updateCurrentUser as Mock).mockResolvedValue(updatedUser);

          await act(async () => {
              const res = await useAuthStore.getState().updateUserProfile(updateData);
              expect(res).toEqual(updatedUser);
          });

          expect(useAuthStore.getState().user).toEqual(updatedUser);
      });
  });

  describe("selectors", () => {
      it("getUser returns user", async () => {
          const { useAuthStore, authSelectors } = await import("@/stores/auth-store");
          const mockUser = { id: "1", email: "test@example.com" } as User;
          
          act(() => { useAuthStore.getState().setUser(mockUser); });
          expect(authSelectors.getUser(useAuthStore.getState())).toEqual(mockUser);
      });

      it("role checks work correctly", async () => {
          const { useAuthStore, authSelectors } = await import("@/stores/auth-store");
          
          // Admin
          act(() => { useAuthStore.getState().setUser({ role: "admin" } as User); });
          const state = useAuthStore.getState();
          expect(authSelectors.isAdmin(state)).toBe(true);
          expect(authSelectors.isManagerOrHigher(state)).toBe(true);
          expect(authSelectors.hasRole("admin")(state)).toBe(true);

          // Manager
           act(() => { useAuthStore.getState().setUser({ role: "manager" } as User); });
           const stateMgr = useAuthStore.getState();
           expect(authSelectors.isAdmin(stateMgr)).toBe(false);
           expect(authSelectors.isManagerOrHigher(stateMgr)).toBe(true);

           // User
           act(() => { useAuthStore.getState().setUser({ role: "member" } as unknown as User); });
           const stateUser = useAuthStore.getState();
           expect(authSelectors.isAdmin(stateUser)).toBe(false);
           expect(authSelectors.isManagerOrHigher(stateUser)).toBe(false);
      });

      it("getUserInitials returns correct initials", async () => {
          const { useAuthStore, authSelectors } = await import("@/stores/auth-store");
          
          // 1. First & Last
          act(() => { useAuthStore.getState().setUser({ firstName: "John", lastName: "Doe" } as User); });
          expect(authSelectors.getUserInitials(useAuthStore.getState())).toBe("JD");

          // 2. First only
          act(() => { useAuthStore.getState().setUser({ firstName: "John", lastName: "" } as User); });
          expect(authSelectors.getUserInitials(useAuthStore.getState())).toBe("J");

          // 3. Last only
          act(() => { useAuthStore.getState().setUser({ firstName: "", lastName: "Doe" } as User); });
          expect(authSelectors.getUserInitials(useAuthStore.getState())).toBe("D");

          // 4. Username
          act(() => { useAuthStore.getState().setUser({ username: "johndoe" } as User); });
          expect(authSelectors.getUserInitials(useAuthStore.getState())).toBe("J");
          
          // 5. Email
           act(() => { useAuthStore.getState().setUser({ email: "test@example.com" } as User); });
           expect(authSelectors.getUserInitials(useAuthStore.getState())).toBe("T");
           
          // 6. Fallback
          act(() => { useAuthStore.getState().setUser({} as User); });
          expect(authSelectors.getUserInitials(useAuthStore.getState())).toBe("U");
      });
  });
});

