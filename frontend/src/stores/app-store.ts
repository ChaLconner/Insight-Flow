// ===========================================
// Zustand App Store
// Refactored to use Slice Pattern
// ===========================================

import { create } from "zustand";
import { persist } from "zustand/middleware";
import { toast } from "sonner";
import { createUISlice, UIState } from "./slices/ui-slice";
import { createFormSlice, FormState } from "./slices/form-slice";
import { createUserSlice, UserState } from "./slices/user-slice";

// ===========================================
// Re-export types for backward compatibility
// ===========================================

export * from "./slices/ui-slice";
export * from "./slices/form-slice";
export * from "./slices/user-slice";

// ===========================================
// App Store Interface
// ===========================================

// Combine all slice states into one AppState
export type AppState = UIState & FormState & UserState & {
  resetAppState: () => void;
};

export const useAppStore = create<AppState>()(
  persist(
    (...a) => ({
      ...createUISlice(...a),
      ...createFormSlice(...a),
      ...createUserSlice(...a),

      // Global Reset
      resetAppState: () => {
        const [set, get] = a;
        // Call reset on slices that support it or reset manually
        get().resetUIState();
        
        // Manual reset for others if they don't have dedicated reset methods exposed yet
        set({
          activeForm: null,
          formData: {},
          formErrors: {},
          forms: {},
          userPreferences: {},
          currentProjectId: null,
        });
      },
    }),
    {
      name: "insight-flow-app",
      partialize: (state) => ({
        sidebarCollapsed: state.sidebarCollapsed,
        currentPage: state.currentPage,
        formData: state.formData,
        formErrors: state.formErrors,
        userPreferences: state.userPreferences,
        currentProjectId: state.currentProjectId,
        isDarkMode: state.isDarkMode,
      }),
    },
  ),
);

// ===========================================
// App Store Actions (Legacy Facade)
// ===========================================

export const appActions = {
  // Utility functions
  generateId: () =>
    `id-${Date.now()}-${Math.random().toString(36).substring(2, 11)}`,

  // Show success message
  showSuccess: (title: string, message: string, duration?: number) => {
    toast.success(title, {
      description: message,
      duration: duration || 4000,
    });
    return `toast-${Date.now()}`;
  },

  // Show error message
  showError: (title: string, message: string, duration?: number) => {
    toast.error(title, {
      description: message,
      duration: duration || 5000,
    });
    return `toast-${Date.now()}`;
  },

  // Show warning message
  showWarning: (title: string, message: string, duration?: number) => {
    toast.warning(title, {
      description: message,
      duration: duration || 5000,
    });
    return `toast-${Date.now()}`;
  },

  // Show info message
  showInfo: (title: string, message: string, duration?: number) => {
    toast.info(title, {
      description: message,
      duration: duration || 4000,
    });
    return `toast-${Date.now()}`;
  },

  // Navigation helpers
  navigateTo: (
    path: string,
    breadcrumbs?: Array<{ label: string; href?: string }>,
  ) => {
    const { setCurrentPage, setBreadcrumbs } = useAppStore.getState();
    setCurrentPage(path);
    if (breadcrumbs) {
      setBreadcrumbs(breadcrumbs);
    }
  },

  // Modal helpers (delegating to store actions)
  openFormModal: (formId: string, initialData?: Record<string, unknown>) => {
    useAppStore.getState().openFormModal(formId, initialData);
  },

  closeFormModal: () => {
    useAppStore.getState().closeFormModal();
  },
};

// ===========================================
// App Store Selectors
// ===========================================

export const appSelectors = {
  // UI Selectors
  isSidebarCollapsed: (state: AppState) => state.sidebarCollapsed,
  isSideNavOpen: (state: AppState) => state.isSideNavOpen,
  getCurrentPage: (state: AppState) => state.currentPage,
  getBreadcrumbs: (state: AppState) => state.breadcrumbs,

  // Modal Selectors
  getActiveModal: (state: AppState) => state.activeModal,
  getModalData: (state: AppState) => state.modalData,
  isModalOpen: (state: AppState) => (modalId: string) =>
    state.activeModal === modalId,
  getModals: (state: AppState) => state.modals,

  // Loading Selectors
  isGlobalLoading: (state: AppState) => state.globalLoading,
  isPageLoading: (state: AppState) => (page: string) =>
    state.pageLoading[page] || false,
  isLoading: (state: AppState) => state.isLoading,

  // Alert Selectors
  getAlerts: (state: AppState) => state.alerts,
  getAlertsByType: (state: AppState) => (type: AppState["alerts"][0]["type"]) =>
    state.alerts.filter((alert) => alert.type === type),

  // Form Selectors
  getActiveForm: (state: AppState) => state.activeForm,
  getFormData: (state: AppState) => (formId?: string) =>
    formId && state.activeForm === formId ? state.formData : {},
  getFormErrors: (state: AppState) => state.formErrors,
  getForms: (state: AppState) => state.forms,

  // Search Selectors
  getGlobalSearch: (state: AppState) => state.globalSearch,
  getSearch: (state: AppState) => state.search,

  // User Preferences
  getCurrentProjectId: (state: AppState) => state.currentProjectId,
  getUserPreferences: (state: AppState) => state.userPreferences,

  // UI State
  isFullscreen: (state: AppState) => state.isFullscreen,
  isDarkMode: (state: AppState) => state.isDarkMode,
} as const;

// Auto-cleanup alerts on unmount
if (typeof window !== "undefined") {
  document.addEventListener("visibilitychange", () => {
    if (document.hidden) {
      const { clearAlerts } = useAppStore.getState();
      clearAlerts();
    }
  });
}
