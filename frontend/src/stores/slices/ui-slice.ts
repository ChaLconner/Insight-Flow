import { StateCreator } from "zustand";

import type { BreadcrumbItem, Notification } from "@/types";
import { FormState } from "./form-slice";
import { generateId } from "@/lib/utils";

// Toast data type
export interface ToastData {
  id: string;
  type: "success" | "error" | "warning" | "info";
  title: string;
  message: string;
  duration?: number;
  action?: {
    label: string;
    onClick: () => void;
  };
}

// Search result type
export interface SearchResult {
  id: string;
  type: "project" | "task" | "user";
  title: string;
  description?: string;
  url: string;
}

// Search state type
export interface SearchState {
  query: string;
  filters: Record<string, unknown>;
  isActive: boolean;
  isSearching: boolean;
}

export interface ModalData {
  formId?: string;
  [key: string]: unknown;
}

export interface UIState {
  // UI State
  sidebarCollapsed: boolean;
  isSideNavOpen: boolean; // Alias for sidebarCollapsed
  currentPage: string;
  breadcrumbs: Array<{ label: string; href?: string }>;

  // Modal State
  activeModal: string | null;
  modalData: Record<string, unknown>;
  modals: Array<{ id: string; data: ModalData }>; // For backward compatibility

  // Loading States
  globalLoading: boolean;
  pageLoading: Record<string, boolean>;
  isLoading: boolean; // Alias for globalLoading

  // Alert/Toast State
  alerts: Array<{
    id: string;
    type: "success" | "error" | "warning" | "info";
    title: string;
    message: string;
    duration?: number;
    action?: {
      label: string;
      onClick: () => void;
    };
  }>;
  toasts: Array<ToastData>; // For backward compatibility

  // Search State
  globalSearch: {
    query: string;
    isOpen: boolean;
    results: SearchResult[];
    isLoading: boolean;
    filters?: Record<string, unknown>;
    isActive?: boolean;
    isSearching?: boolean;
  };
  search: SearchState; // For backward compatibility

  // UI Settings
  isFullscreen: boolean;
  isDarkMode: boolean; // For theme integration

  // Actions
  setSidebarCollapsed: (collapsed: boolean) => void;
  toggleSidebar: () => void;
  toggleSideNav: () => void; // Alias
  setCurrentPage: (page: string) => void;
  setBreadcrumbs: (
    breadcrumbs: Array<{ label: string; href?: string }>,
  ) => void;

  // Modal Actions
  openModal: (modalId: string, data?: Record<string, unknown>) => void;
  closeModal: () => void;
  setModalData: (data: Record<string, unknown>) => void;
  showModal: (id: string, data?: Record<string, unknown>) => void; // Alias
  hideModal: (id: string) => void; // Alias
  closeAllModals: () => void;

  // Loading Actions
  setGlobalLoading: (loading: boolean) => void;
  setPageLoading: (page: string, loading: boolean) => void;
  setLoading: (loading: { isLoading: boolean; message?: string }) => void; // Enhanced

  // Alert Actions
  addAlert: (alert: Omit<UIState["alerts"][0], "id">) => string;
  removeAlert: (id: string) => void;
  clearAlerts: () => void;

  // Search Actions
  setGlobalSearchQuery: (query: string) => void;
  setGlobalSearchOpen: (open: boolean) => void;
  setGlobalSearchResults: (results: SearchResult[]) => void;
  setGlobalSearchLoading: (loading: boolean) => void;
  clearGlobalSearch: () => void;
  setSearch: (search: SearchState) => void; // Alias
  clearSearch: () => void; // Alias

  // UI Actions
  setFullscreen: (fullscreen: boolean) => void;
  toggleFullscreen: () => void;
  setDarkMode: (dark: boolean) => void; // For theme integration
  toggleDarkMode: () => void; // For theme integration

  // Advanced Actions
  setPageTitle: (title: string) => void;
  showToast: (toast: ToastData) => void;
  hideToast: (id: string) => void;
  addNotification: (notification: Notification) => void;
  removeNotification: (id: string) => void;
  clearNotifications: () => void;
  navigateWithBreadcrumb: (item: BreadcrumbItem) => void;
  resetUIState: () => void;
  
  // Cross-slice helpers (need type intersection in usage)
  openFormModal: (formId: string, initialData?: Record<string, unknown>) => void;
  closeFormModal: () => void;
}

export const createUISlice: StateCreator<UIState & FormState, [], [], UIState> = (set, get) => ({
  // Initial state
  sidebarCollapsed: false,
  isSideNavOpen: false, // Alias for sidebarCollapsed
  currentPage: "/dashboard",
  breadcrumbs: [{ label: "Dashboard", href: "/dashboard" }],

  activeModal: null,
  modalData: {},
  modals: [], // For backward compatibility

  globalLoading: false,
  pageLoading: {},
  isLoading: false, // Alias for globalLoading

  alerts: [],
  toasts: [], // For backward compatibility
  
  globalSearch: {
    query: "",
    isOpen: false,
    results: [],
    isLoading: false,
    filters: {},
    isActive: false,
    isSearching: false,
  },
  search: { query: "", filters: {}, isActive: false, isSearching: false }, // For backward compatibility

  isFullscreen: false,
  isDarkMode: false, // For theme integration

  // UI Actions
  setSidebarCollapsed: (collapsed) =>
    set({
      sidebarCollapsed: collapsed,
      isSideNavOpen: collapsed, // Keep aliases in sync
    }),

  toggleSidebar: () =>
    set((state) => ({
      sidebarCollapsed: !state.sidebarCollapsed,
      isSideNavOpen: !state.isSideNavOpen, // Keep aliases in sync
    })),

  toggleSideNav: () =>
    set((state) => ({
      sidebarCollapsed: !state.sidebarCollapsed,
      isSideNavOpen: !state.isSideNavOpen, // Keep aliases in sync
    })),

  setCurrentPage: (page) => set({ currentPage: page }),

  setBreadcrumbs: (breadcrumbs) => set({ breadcrumbs }),

  // Modal Actions
  openModal: (modalId, data) =>
    set({
      activeModal: modalId,
      modalData: data ?? {},
    }),

  closeModal: () =>
    set({
      activeModal: null,
      modalData: {},
    }),

  setModalData: (data) =>
    set((state) => ({
      modalData: { ...state.modalData, ...data },
    })),

  // Modal Actions (add aliases)
  showModal: (id, data = {}) =>
    set((state) => ({
      activeModal: id,
      modalData: data,
      modals: [...(state.modals || []), { id, data }], // Add to modals array
    })),

  hideModal: (id) =>
    set((state) => ({
      activeModal: null,
      modals: state.modals.filter((m) => m.id !== id),
    })),

  closeAllModals: () =>
    set({
      activeModal: null,
      modals: [],
    }),

  // Loading Actions
  setGlobalLoading: (loading) =>
    set({
      globalLoading: loading,
      isLoading: loading, // Keep aliases in sync
    }),

  setPageLoading: (page, loading) =>
    set((state) => ({
      pageLoading: {
        ...state.pageLoading,
        [page]: loading,
      },
    })),

  setLoading: (loading) =>
    set({
      globalLoading: loading.isLoading,
      isLoading: loading.isLoading, // Keep aliases in sync
    }),

  // Alert Actions
  addAlert: (alert) => {
    const id = `alert-${Date.now()}-${generateId(8)}`;

    set((state) => ({
      alerts: [...state.alerts, { ...alert, id }],
    }));

    // Auto-remove alert after duration
    if (alert.duration !== 0) {
      setTimeout(() => {
        get().removeAlert(id);
      }, alert.duration || 5000);
    }

    return id;
  },

  removeAlert: (id) =>
    set((state) => ({
      alerts: state.alerts.filter((alert) => alert.id !== id),
    })),

  clearAlerts: () => set({ alerts: [] }),

  // Search Actions
  setGlobalSearchQuery: (query) =>
    set((state) => ({
      globalSearch: { ...state.globalSearch, query },
    })),

  setGlobalSearchOpen: (open) =>
    set((state) => ({
      globalSearch: { ...state.globalSearch, isOpen: open },
    })),

  setGlobalSearchResults: (results) =>
    set((state) => ({
      globalSearch: { ...state.globalSearch, results },
    })),

  setGlobalSearchLoading: (loading) =>
    set((state) => ({
      globalSearch: { ...state.globalSearch, isLoading: loading },
    })),

  clearGlobalSearch: () =>
    set((state) => ({
      globalSearch: {
        query: "",
        isOpen: state.globalSearch.isOpen,
        results: [],
        isLoading: false,
        filters: {},
        isActive: false,
        isSearching: false,
      },
    })),

  // Search Actions (add aliases)
  setSearch: (search) =>
    set((state) => ({
      globalSearch: { ...state.globalSearch, ...search },
      search: { ...state.search, ...search },
    })),

  clearSearch: () =>
    set((state) => ({
      globalSearch: {
        query: "",
        isOpen: state.globalSearch.isOpen,
        results: [],
        isLoading: false,
        filters: {},
        isActive: false,
        isSearching: false,
      },
      search: {
        query: "",
        filters: {},
        isActive: false,
        isSearching: false,
      },
    })),

  // UI Actions
  setFullscreen: (fullscreen) => set({ isFullscreen: fullscreen }),

  toggleFullscreen: () =>
    set((state) => ({ isFullscreen: !state.isFullscreen })),

  setDarkMode: (dark) => set({ isDarkMode: dark }),

  toggleDarkMode: () => set((state) => ({ isDarkMode: !state.isDarkMode })),

  // Advanced Actions
  setPageTitle: (title) => {
    if (typeof window !== "undefined") {
      document.title = title;
    }
  },

  showToast: (toastItem) =>
    set((state) => ({
      toasts: [...state.toasts, { ...toastItem, id: `toast-${Date.now()}` }],
    })),

  hideToast: (id) =>
    set((state) => ({
      toasts: state.toasts.filter((t) => t.id !== id),
    })),

  addNotification: (notification) => {
    // Add to alerts for compatibility
    get().addAlert({
      type: "info",
      title: notification.title || "Notification",
      message: notification.message || "",
      duration: 5000,
    });
  },

  removeNotification: (id) => {
    // Remove from alerts for compatibility
    get().removeAlert(id);
  },

  clearNotifications: () => {
    get().clearAlerts();
  },

  navigateWithBreadcrumb: (item) => {
    if (item.href && typeof window !== "undefined") {
      window.location.href = item.href;
    }
  },
  
  // Implementation of cross-slice helpers
  openFormModal: (formId, initialData) => {
    // Requires FormSlice state/actions availability
    get().openModal("form-modal", { formId });
    get().setActiveForm(formId);
    if (initialData) {
      get().updateFormData(initialData);
    }
  },
  
  closeFormModal: () => {
    const { activeForm } = get();
    get().closeModal();
    get().clearFormData(activeForm || undefined);
  },

  resetUIState: () => {
    set({
      sidebarCollapsed: false,
      isSideNavOpen: false,
      currentPage: "/dashboard",
      breadcrumbs: [{ label: "Dashboard", href: "/dashboard" }],
      activeModal: null,
      modalData: {},
      modals: [],
      globalLoading: false,
      isLoading: false,
      pageLoading: {},
      alerts: [],
      toasts: [],
      globalSearch: {
        query: "",
        isOpen: false,
        results: [],
        isLoading: false,
        filters: {},
        isActive: false,
        isSearching: false,
      },
      search: {
        query: "",
        filters: {},
        isActive: false,
        isSearching: false,
      },
      isFullscreen: false,
      isDarkMode: false,
    });
  },
});
