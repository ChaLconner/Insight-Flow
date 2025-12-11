// ===========================================
// Zustand App Store
// ===========================================

import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { toast } from 'sonner';

interface AppState {
  // UI State
  sidebarCollapsed: boolean;
  isSideNavOpen: boolean; // Alias for sidebarCollapsed
  currentPage: string;
  breadcrumbs: Array<{ label: string; href?: string }>;

  // Modal State
  activeModal: string | null;
  modalData: Record<string, any>;
  modals: Array<any>; // For backward compatibility

  // Loading States
  globalLoading: boolean;
  pageLoading: Record<string, boolean>;
  isLoading: boolean; // Alias for globalLoading

  // Alert/Toast State
  alerts: Array<{
    id: string;
    type: 'success' | 'error' | 'warning' | 'info';
    title: string;
    message: string;
    duration?: number;
    action?: {
      label: string;
      onClick: () => void;
    };
  }>;
  toasts: Array<any>; // For backward compatibility

  // Form State
  activeForm: string | null;
  formData: Record<string, any>;
  formErrors: Record<string, string>;
  forms: Record<string, any>; // For backward compatibility

  // Search State
  globalSearch: {
    query: string;
    isOpen: boolean;
    results: any[];
    isLoading: boolean;
    filters?: Record<string, any>;
    isActive?: boolean;
    isSearching?: boolean;
  };
  search: any; // For backward compatibility

  // User Preferences
  userPreferences: Record<string, any>;
  currentProjectId: string | null;

  // Fullscreen
  isFullscreen: boolean;
  isDarkMode: boolean; // For theme integration

  // Actions
  setSidebarCollapsed: (collapsed: boolean) => void;
  toggleSidebar: () => void;
  toggleSideNav: () => void; // Alias
  setCurrentPage: (page: string) => void;
  setBreadcrumbs: (breadcrumbs: Array<{ label: string; href?: string }>) => void;

  // Modal Actions
  openModal: (modalId: string, data?: any) => void;
  closeModal: () => void;
  setModalData: (data: Record<string, any>) => void;
  showModal: (id: string, data?: any) => void; // Alias
  hideModal: (id: string) => void; // Alias
  closeAllModals: () => void;

  // Loading Actions
  setGlobalLoading: (loading: boolean) => void;
  setPageLoading: (page: string, loading: boolean) => void;
  setLoading: (loading: { isLoading: boolean; message?: string }) => void; // Enhanced

  // Alert Actions
  addAlert: (alert: Omit<AppState['alerts'][0], 'id'>) => string;
  removeAlert: (id: string) => void;
  clearAlerts: () => void;

  // Form Actions
  setActiveForm: (formId: string | null) => void;
  updateFormData: (data: Record<string, any>) => void;
  setFormErrors: (errors: Record<string, string>) => void;
  clearFormData: (formId?: string) => void;
  updateForm: (formId: string, data: any) => void; // Alias
  clearForm: (formId: string) => void; // Alias

  // Search Actions
  setGlobalSearchQuery: (query: string) => void;
  setGlobalSearchOpen: (open: boolean) => void;
  setGlobalSearchResults: (results: any[]) => void;
  setGlobalSearchLoading: (loading: boolean) => void;
  clearGlobalSearch: () => void;
  setSearch: (search: any) => void; // Alias
  clearSearch: () => void; // Alias

  // User Preferences
  setCurrentProjectId: (id: string | null) => void;
  updateUserPreferences: (preferences: Record<string, any>) => void;
  setUserPreferences: (preferences: Record<string, any>) => void; // Alias

  // UI Actions
  setFullscreen: (fullscreen: boolean) => void;
  toggleFullscreen: () => void;
  setDarkMode: (dark: boolean) => void; // For theme integration
  toggleDarkMode: () => void; // For theme integration

  // Advanced Actions
  setPageTitle: (title: string) => void;
  showToast: (toast: any) => void;
  hideToast: (id: string) => void;
  addNotification: (notification: any) => void;
  removeNotification: (id: string) => void;
  clearNotifications: () => void;
  navigateWithBreadcrumb: (item: any) => void;
  resetAppState: () => void;
}

export const useAppStore = create<AppState>()(
  persist(
    (set, get) => ({
      // Initial state
      sidebarCollapsed: false,
      isSideNavOpen: false, // Alias for sidebarCollapsed
      currentPage: '/dashboard',
      breadcrumbs: [{ label: 'Dashboard', href: '/dashboard' }],

      activeModal: null,
      modalData: {},
      modals: [], // For backward compatibility

      globalLoading: false,
      pageLoading: {},
      isLoading: false, // Alias for globalLoading

      alerts: [],
      toasts: [], // For backward compatibility

      activeForm: null,
      formData: {},
      formErrors: {},
      forms: {}, // For backward compatibility

      globalSearch: {
        query: '',
        isOpen: false,
        results: [],
        isLoading: false,
        filters: {},
        isActive: false,
        isSearching: false,
      },
      search: { query: '', filters: {}, isActive: false, isSearching: false }, // For backward compatibility

      userPreferences: {},
      currentProjectId: null,

      isFullscreen: false,
      isDarkMode: false, // For theme integration

      // UI Actions
      setSidebarCollapsed: (collapsed) => set({
        sidebarCollapsed: collapsed,
        isSideNavOpen: collapsed // Keep aliases in sync
      }),

      toggleSidebar: () => set((state) => ({
        sidebarCollapsed: !state.sidebarCollapsed,
        isSideNavOpen: !state.isSideNavOpen // Keep aliases in sync
      })),

      toggleSideNav: () => set((state) => ({
        sidebarCollapsed: !state.sidebarCollapsed,
        isSideNavOpen: !state.isSideNavOpen // Keep aliases in sync
      })),

      setCurrentPage: (page) => set({ currentPage: page }),

      setBreadcrumbs: (breadcrumbs) => set({ breadcrumbs }),

      // Modal Actions
      openModal: (modalId, data) => set({
        activeModal: modalId,
        modalData: data || {}
      }),

      closeModal: () => set({
        activeModal: null,
        modalData: {}
      }),

      setModalData: (data) => set((state) => ({
        modalData: { ...state.modalData, ...data }
      })),

      // Modal Actions (add aliases)
      showModal: (id, data) => set({
        activeModal: id,
        modalData: data || {},
        modals: [...(get().modals || []), { id, data }] // Add to modals array
      }),

      hideModal: (id) => set((state) => ({
        activeModal: null,
        modals: state.modals.filter(m => m.id !== id)
      })),

      closeAllModals: () => set({
        activeModal: null,
        modals: []
      }),

      // Loading Actions
      setGlobalLoading: (loading) => set({
        globalLoading: loading,
        isLoading: loading // Keep aliases in sync
      }),

      setPageLoading: (page, loading) => set((state) => ({
        pageLoading: {
          ...state.pageLoading,
          [page]: loading,
        }
      })),

      setLoading: (loading) => set({
        globalLoading: loading.isLoading,
        isLoading: loading.isLoading // Keep aliases in sync
      }),

      // Alert Actions
      addAlert: (alert) => {
        const id = `alert-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;

        set((state) => ({
          alerts: [...state.alerts, { ...alert, id }]
        }));

        // Auto-remove alert after duration
        if (alert.duration !== 0) {
          setTimeout(() => {
            get().removeAlert(id);
          }, alert.duration || 5000);
        }

        return id;
      },

      removeAlert: (id) => set((state) => ({
        alerts: state.alerts.filter(alert => alert.id !== id)
      })),

      clearAlerts: () => set({ alerts: [] }),

      // Form Actions
      setActiveForm: (formId) => set({ activeForm: formId }),

      updateFormData: (data) => set((state) => ({
        formData: { ...state.formData, ...data }
      })),

      setFormErrors: (errors) => set({ formErrors: errors }),

      clearFormData: (formId) => set((state) => {
        if (formId && state.activeForm === formId) {
          return {
            activeForm: null,
            formData: {},
            formErrors: {},
          };
        }
        return state;
      }),

      // Form Actions (add aliases)
      updateForm: (formId, data) => set((state) => ({
        forms: { ...state.forms, [formId]: data },
        formData: data.data || {},
        formErrors: data.errors || {},
      })),

      clearForm: (formId) => set((state) => {
        const { [formId]: _removed, ...remainingForms } = state.forms;
        if (state.activeForm === formId) {
          return {
            activeForm: null,
            formData: {},
            formErrors: {},
            forms: remainingForms,
          };
        }
        return { forms: remainingForms };
      }),

      // Search Actions
      setGlobalSearchQuery: (query) => set((state) => ({
        globalSearch: { ...state.globalSearch, query }
      })),

      setGlobalSearchOpen: (open) => set((state) => ({
        globalSearch: { ...state.globalSearch, isOpen: open }
      })),

      setGlobalSearchResults: (results) => set((state) => ({
        globalSearch: { ...state.globalSearch, results }
      })),

      setGlobalSearchLoading: (loading) => set((state) => ({
        globalSearch: { ...state.globalSearch, isLoading: loading }
      })),

      clearGlobalSearch: () => set((state) => ({
        globalSearch: {
          query: '',
          isOpen: state.globalSearch.isOpen,
          results: [],
          isLoading: false,
          filters: {},
          isActive: false,
          isSearching: false,
        }
      })),

      // Search Actions (add aliases)
      setSearch: (search) => set((state) => ({
        globalSearch: { ...state.globalSearch, ...search },
        search: { ...state.search, ...search }
      })),

      clearSearch: () => set((state) => ({
        globalSearch: {
          query: '',
          isOpen: state.globalSearch.isOpen,
          results: [],
          isLoading: false,
          filters: {},
          isActive: false,
          isSearching: false,
        },
        search: {
          query: '',
          filters: {},
          isActive: false,
          isSearching: false,
        }
      })),

      // User Preferences Actions
      setCurrentProjectId: (id) => set({ currentProjectId: id }),

      updateUserPreferences: (preferences) => set((state) => ({
        userPreferences: { ...state.userPreferences, ...preferences }
      })),

      setUserPreferences: (preferences) => set((state) => ({
        userPreferences: { ...state.userPreferences, ...preferences }
      })),

      // UI Actions
      setFullscreen: (fullscreen) => set({ isFullscreen: fullscreen }),

      toggleFullscreen: () => set((state) => ({ isFullscreen: !state.isFullscreen })),

      setDarkMode: (dark) => set({ isDarkMode: dark }),

      toggleDarkMode: () => set((state) => ({ isDarkMode: !state.isDarkMode })),

      // Advanced Actions
      setPageTitle: (title) => {
        if (typeof window !== 'undefined') {
          document.title = title;
        }
      },

      showToast: (toast) => set((state) => ({
        toasts: [...state.toasts, { ...toast, id: `toast-${Date.now()}` }]
      })),

      hideToast: (id) => set((state) => ({
        toasts: state.toasts.filter(t => t.id !== id)
      })),

      addNotification: (notification) => {
        // Add to alerts for compatibility
        get().addAlert({
          type: 'info',
          title: notification.title || 'Notification',
          message: notification.message || '',
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
        if (item.href && typeof window !== 'undefined') {
          window.location.href = item.href;
        }
      },

      resetAppState: () => {
        set({
          sidebarCollapsed: false,
          isSideNavOpen: false,
          currentPage: '/dashboard',
          breadcrumbs: [{ label: 'Dashboard', href: '/dashboard' }],
          activeModal: null,
          modalData: {},
          modals: [],
          globalLoading: false,
          isLoading: false,
          pageLoading: {},
          alerts: [],
          toasts: [],
          activeForm: null,
          formData: {},
          formErrors: {},
          forms: {},
          globalSearch: {
            query: '',
            isOpen: false,
            results: [],
            isLoading: false,
            filters: {},
            isActive: false,
            isSearching: false,
          },
          search: {
            query: '',
            filters: {},
            isActive: false,
            isSearching: false,
          },
          userPreferences: {},
          currentProjectId: null,
          isFullscreen: false,
          isDarkMode: false,
        });
      },
    }),
    {
      name: 'insight-flow-app',
      partialize: (state) => ({
        sidebarCollapsed: state.sidebarCollapsed,
        currentPage: state.currentPage,
        formData: state.formData,
        formErrors: state.formErrors,
      }),
    }
  )
);

// ===========================================
// App Store Selectors
// ===========================================

export const appSelectors = {
  // UI Selectors
  isSidebarCollapsed: (state: AppState) => state.sidebarCollapsed,
  isSideNavOpen: (state: AppState) => state.isSideNavOpen, // Alias
  getCurrentPage: (state: AppState) => state.currentPage,
  getBreadcrumbs: (state: AppState) => state.breadcrumbs,

  // Modal Selectors
  getActiveModal: (state: AppState) => state.activeModal,
  getModalData: (state: AppState) => state.modalData,
  isModalOpen: (state: AppState) => (modalId: string) => state.activeModal === modalId,
  getModals: (state: AppState) => state.modals, // For compatibility

  // Loading Selectors
  isGlobalLoading: (state: AppState) => state.globalLoading,
  isPageLoading: (state: AppState) => (page: string) => state.pageLoading[page] || false,
  isLoading: (state: AppState) => state.isLoading, // Alias

  // Alert Selectors
  getAlerts: (state: AppState) => state.alerts,
  getAlertsByType: (state: AppState) => (type: AppState['alerts'][0]['type']) =>
    state.alerts.filter(alert => alert.type === type),

  // Form Selectors
  getActiveForm: (state: AppState) => state.activeForm,
  getFormData: (state: AppState) => (formId?: string) =>
    formId && state.activeForm === formId ? state.formData : {},
  getFormErrors: (state: AppState) => state.formErrors,
  getForms: (state: AppState) => state.forms, // For compatibility

  // Search Selectors
  getGlobalSearch: (state: AppState) => state.globalSearch,
  getSearch: (state: AppState) => state.search, // For compatibility

  // User Preferences
  getCurrentProjectId: (state: AppState) => state.currentProjectId,
  getUserPreferences: (state: AppState) => state.userPreferences,

  // UI State
  isFullscreen: (state: AppState) => state.isFullscreen,
  isDarkMode: (state: AppState) => state.isDarkMode, // For theme integration
} as const;

// ===========================================
// App Store Actions
// ===========================================

export const appActions = {
  // Utility functions
  generateId: () => `id-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,

  // Show success message
  showSuccess: (title: string, message: string, duration?: number) => {
    toast.success(title, {
      description: message,
      duration: duration || 4000,
    });
    // Maintain backward compatibility with internal state if needed, or just return an ID
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
  navigateTo: (path: string, breadcrumbs?: Array<{ label: string; href?: string }>) => {
    const { setCurrentPage, setBreadcrumbs } = useAppStore.getState();
    setCurrentPage(path);
    if (breadcrumbs) {
      setBreadcrumbs(breadcrumbs);
    }
  },

  // Modal helpers
  openFormModal: (formId: string, initialData?: Record<string, any>) => {
    const { openModal, setActiveForm, updateFormData } = useAppStore.getState();
    openModal('form-modal', { formId });
    setActiveForm(formId);
    if (initialData) {
      updateFormData(initialData);
    }
  },

  closeFormModal: () => {
    const { closeModal, clearFormData } = useAppStore.getState();
    const { activeForm } = useAppStore.getState();
    closeModal();
    clearFormData(activeForm || undefined);
  },
};

// Auto-cleanup alerts on unmount
if (typeof window !== 'undefined') {
  // Cleanup alerts when page is hidden
  document.addEventListener('visibilitychange', () => {
    if (document.hidden) {
      const { clearAlerts } = useAppStore.getState();
      clearAlerts();
    }
  });
}