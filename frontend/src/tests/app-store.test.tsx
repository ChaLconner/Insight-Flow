/**
 * Tests for app-store.ts
 * Covers app state management, actions, and selectors.
 */

import { describe, it, expect, beforeEach, vi } from "vitest";
import { renderHook, act } from "@testing-library/react";

// Mock sonner before importing store
vi.mock("sonner", () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
    warning: vi.fn(),
    info: vi.fn(),
  },
}));

describe("AppStore", () => {
  // Import inside tests to ensure mocks are set up
  const getStore = async () => {
    const { useAppStore, appActions, appSelectors } = await import(
      "@/stores/app-store"
    );
    return { useAppStore, appActions, appSelectors };
  };

  beforeEach(async () => {
    vi.clearAllMocks();
    // Reset store state
    const { useAppStore } = await getStore();
    act(() => {
      useAppStore.getState().resetAppState();
    });
  });

  describe("Initial State", () => {
    it("should have default UI state", async () => {
      const { useAppStore, appSelectors } = await getStore();
      const { result } = renderHook(() => useAppStore());

      expect(appSelectors.isSidebarCollapsed(result.current)).toBe(false);
      expect(appSelectors.getCurrentPage(result.current)).toBe("/dashboard");
    });

    it("should have empty form state", async () => {
      const { useAppStore, appSelectors } = await getStore();
      const { result } = renderHook(() => useAppStore());

      expect(appSelectors.getActiveForm(result.current)).toBeNull();
      expect(appSelectors.getFormErrors(result.current)).toEqual({});
    });
  });

  describe("Sidebar Actions", () => {
    it("should toggle sidebar collapsed state", async () => {
      const { useAppStore, appSelectors } = await getStore();
      const { result } = renderHook(() => useAppStore());

      expect(appSelectors.isSidebarCollapsed(result.current)).toBe(false);

      act(() => {
        result.current.setSidebarCollapsed(true);
      });

      expect(appSelectors.isSidebarCollapsed(result.current)).toBe(true);
    });

    it("should toggle sidebar", async () => {
      const { useAppStore, appSelectors } = await getStore();
      const { result } = renderHook(() => useAppStore());

      const initialState = appSelectors.isSidebarCollapsed(result.current);

      act(() => {
        result.current.toggleSidebar();
      });

      expect(appSelectors.isSidebarCollapsed(result.current)).toBe(
        !initialState
      );
    });
  });

  describe("Page Navigation", () => {
    it("should set current page", async () => {
      const { useAppStore, appSelectors } = await getStore();
      const { result } = renderHook(() => useAppStore());

      act(() => {
        result.current.setCurrentPage("/dashboard");
      });

      expect(appSelectors.getCurrentPage(result.current)).toBe("/dashboard");
    });

    it("should set breadcrumbs", async () => {
      const { useAppStore, appSelectors } = await getStore();
      const { result } = renderHook(() => useAppStore());

      const breadcrumbs = [
        { label: "Home", href: "/" },
        { label: "Projects", href: "/projects" },
        { label: "Project 1" },
      ];

      act(() => {
        result.current.setBreadcrumbs(breadcrumbs);
      });

      expect(appSelectors.getBreadcrumbs(result.current)).toEqual(breadcrumbs);
    });
  });

  describe("Modal State", () => {
    it("should open and close modal", async () => {
      const { useAppStore, appSelectors } = await getStore();
      const { result } = renderHook(() => useAppStore());

      act(() => {
        result.current.openModal("test-modal", { foo: "bar" });
      });

      expect(appSelectors.getActiveModal(result.current)).toBe("test-modal");
      expect(appSelectors.getModalData(result.current)).toEqual({ foo: "bar" });

      act(() => {
        result.current.closeModal();
      });

      expect(appSelectors.getActiveModal(result.current)).toBeNull();
    });

    it("should check if modal is open", async () => {
      const { useAppStore, appSelectors } = await getStore();
      const { result } = renderHook(() => useAppStore());

      act(() => {
        result.current.openModal("specific-modal");
      });

      const isSpecificOpen = appSelectors.isModalOpen(result.current);
      expect(isSpecificOpen("specific-modal")).toBe(true);
      expect(isSpecificOpen("other-modal")).toBe(false);
    });
  });

  describe("Loading State", () => {
    it("should set global loading state", async () => {
      const { useAppStore, appSelectors } = await getStore();
      const { result } = renderHook(() => useAppStore());

      act(() => {
        result.current.setGlobalLoading(true);
      });

      expect(appSelectors.isGlobalLoading(result.current)).toBe(true);

      act(() => {
        result.current.setGlobalLoading(false);
      });

      expect(appSelectors.isGlobalLoading(result.current)).toBe(false);
    });

    it("should set page-specific loading state", async () => {
      const { useAppStore, appSelectors } = await getStore();
      const { result } = renderHook(() => useAppStore());

      act(() => {
        result.current.setPageLoading("projects", true);
      });

      const isLoading = appSelectors.isPageLoading(result.current);
      expect(isLoading("projects")).toBe(true);
      expect(isLoading("tasks")).toBe(false);
    });
  });

  describe("Form State", () => {
    it("should open form modal", async () => {
      const { useAppStore, appSelectors } = await getStore();
      const { result } = renderHook(() => useAppStore());

      act(() => {
        result.current.openFormModal("create-project", { name: "Test" });
      });

      expect(appSelectors.getActiveForm(result.current)).toBe("create-project");
    });

    it("should close form modal", async () => {
      const { useAppStore, appSelectors } = await getStore();
      const { result } = renderHook(() => useAppStore());

      act(() => {
        result.current.openFormModal("edit-task");
      });

      expect(appSelectors.getActiveForm(result.current)).toBe("edit-task");

      act(() => {
        result.current.closeFormModal();
      });

      expect(appSelectors.getActiveForm(result.current)).toBeNull();
    });

    it("should set form errors", async () => {
      const { useAppStore, appSelectors } = await getStore();
      const { result } = renderHook(() => useAppStore());

      const errors = { name: "Name is required", email: "Invalid email" };

      act(() => {
        result.current.setFormErrors(errors);
      });

      expect(appSelectors.getFormErrors(result.current)).toEqual(errors);
    });
  });

  describe("Alert Management", () => {
    it("should add and get alerts", async () => {
      const { useAppStore, appSelectors } = await getStore();
      const { result } = renderHook(() => useAppStore());

      act(() => {
        result.current.addAlert({
          type: "success",
          title: "Success",
          message: "Operation completed",
        });
      });

      const alerts = appSelectors.getAlerts(result.current);
      expect(alerts.length).toBeGreaterThan(0);
    });

    it("should remove alert by id", async () => {
      const { useAppStore, appSelectors } = await getStore();
      const { result } = renderHook(() => useAppStore());

      act(() => {
        result.current.addAlert({
          type: "error",
          title: "Error",
          message: "Something went wrong",
        });
      });

      // Get the alert that was just added
      const alerts = appSelectors.getAlerts(result.current);
      const alertToRemove = alerts[0];

      if (alertToRemove) {
        act(() => {
          result.current.removeAlert(alertToRemove.id);
        });

        const finalAlerts = appSelectors.getAlerts(result.current);
        expect(
          finalAlerts.find((a) => a.id === alertToRemove.id)
        ).toBeUndefined();
      }
    });

    it("should clear all alerts", async () => {
      const { useAppStore, appSelectors } = await getStore();
      const { result } = renderHook(() => useAppStore());

      act(() => {
        result.current.addAlert({
          type: "info",
          title: "Info",
          message: "M",
        });
        result.current.addAlert({
          type: "warning",
          title: "Warning",
          message: "M",
        });
      });

      act(() => {
        result.current.clearAlerts();
      });

      expect(appSelectors.getAlerts(result.current).length).toBe(0);
    });
  });

  describe("Search State", () => {
    it("should set global search query", async () => {
      const { useAppStore, appSelectors } = await getStore();
      const { result } = renderHook(() => useAppStore());

      act(() => {
        result.current.setGlobalSearchQuery("test query");
      });

      const globalSearch = appSelectors.getGlobalSearch(result.current);
      expect(globalSearch.query).toBe("test query");
    });

    it("should set search state", async () => {
      const { useAppStore, appSelectors } = await getStore();
      const { result } = renderHook(() => useAppStore());

      act(() => {
        result.current.setSearch({
          query: "project",
          filters: { status: "active" },
          isActive: true,
          isSearching: false,
        });
      });

      const search = appSelectors.getSearch(result.current);
      expect(search).toBeDefined();
      expect(search.query).toBe("project");
    });
  });

  describe("User Preferences", () => {
    it("should set current project id", async () => {
      const { useAppStore, appSelectors } = await getStore();
      const { result } = renderHook(() => useAppStore());

      act(() => {
        result.current.setCurrentProjectId("project-123");
      });

      expect(appSelectors.getCurrentProjectId(result.current)).toBe(
        "project-123"
      );
    });

    it("should update user preferences", async () => {
      const { useAppStore, appSelectors } = await getStore();
      const { result } = renderHook(() => useAppStore());

      act(() => {
        result.current.setUserPreferences({
          defaultView: "list",
          compactMode: true,
        });
      });

      const prefs = appSelectors.getUserPreferences(result.current);
      expect(prefs).toEqual({
        defaultView: "list",
        compactMode: true,
      });
    });
  });

  describe("UI State", () => {
    it("should toggle fullscreen", async () => {
      const { useAppStore, appSelectors } = await getStore();
      const { result } = renderHook(() => useAppStore());

      act(() => {
        result.current.setFullscreen(true);
      });

      expect(appSelectors.isFullscreen(result.current)).toBe(true);

      act(() => {
        result.current.setFullscreen(false);
      });

      expect(appSelectors.isFullscreen(result.current)).toBe(false);
    });
  });

  describe("App Actions", () => {
    it("should generate unique ids", async () => {
      const { appActions } = await getStore();

      const id1 = appActions.generateId();
      const id2 = appActions.generateId();

      expect(id1).not.toBe(id2);
      expect(id1.startsWith("id-")).toBe(true);
    });

    it("should navigate to page with breadcrumbs", async () => {
      const { useAppStore, appActions, appSelectors } = await getStore();

      const breadcrumbs = [{ label: "Home", href: "/" }, { label: "Settings" }];

      act(() => {
        appActions.navigateTo("/settings", breadcrumbs);
      });

      const state = useAppStore.getState();
      expect(appSelectors.getCurrentPage(state)).toBe("/settings");
      expect(appSelectors.getBreadcrumbs(state)).toEqual(breadcrumbs);
    });
  });

  describe("Reset State", () => {
    it("should reset app state", async () => {
      const { useAppStore, appSelectors } = await getStore();
      const { result } = renderHook(() => useAppStore());

      // Modify state
      act(() => {
        result.current.setCurrentPage("/modified");
        result.current.setSidebarCollapsed(true);
        result.current.setCurrentProjectId("project-xyz");
      });

      // Reset
      act(() => {
        result.current.resetAppState();
      });

      // Check reset values
      expect(appSelectors.getActiveForm(result.current)).toBeNull();
      expect(appSelectors.getCurrentProjectId(result.current)).toBeNull();
    });
  });

  describe("Selectors", () => {
    it("should filter alerts by type", async () => {
      const { useAppStore, appSelectors } = await getStore();
      const { result } = renderHook(() => useAppStore());

      act(() => {
        result.current.addAlert({
          type: "success",
          title: "S",
          message: "M",
        });
        result.current.addAlert({
          type: "error",
          title: "E",
          message: "M",
        });
      });

      const getByType = appSelectors.getAlertsByType(result.current);
      const successAlerts = getByType("success");
      const errorAlerts = getByType("error");

      expect(successAlerts.every((a) => a.type === "success")).toBe(true);
      expect(errorAlerts.every((a) => a.type === "error")).toBe(true);
    });
  });
});
