// ===========================================
// useAppState Hook
// ===========================================

import { useCallback } from "react";
import { useAppStore, appSelectors } from "@/stores/app-store";
import { toast } from "sonner";

// Hook for app global state management
const EMPTY_OBJECT: Record<string, unknown> = {};

export const useAppState = () => {
  // Use granular selectors to avoid unnecessary re-renders
  // Each selector subscribes only to the specific state it needs
  const isLoading = useAppStore((state) => appSelectors.isLoading(state));
  const isSideNavOpen = useAppStore((state) => appSelectors.isSideNavOpen(state));
  const isFullscreen = useAppStore((state) => appSelectors.isFullscreen(state));
  const isDarkMode = useAppStore((state) => appSelectors.isDarkMode(state));
  const breadcrumbs = useAppStore((state) => appSelectors.getBreadcrumbs(state));
  const alerts = useAppStore((state) => appSelectors.getAlerts(state));
  const modals = useAppStore((state) => appSelectors.getModals(state));
  const search = useAppStore((state) => appSelectors.getSearch(state));
  const forms = useAppStore((state) => appSelectors.getForms(state));
  const currentProjectId = useAppStore((state) => appSelectors.getCurrentProjectId(state));
  const userPreferences = useAppStore((state) => appSelectors.getUserPreferences(state));

  // Actions — stable references (functions don't change between renders)
  const setLoading = useAppStore((state) => state.setLoading);
  const toggleSideNav = useAppStore((state) => state.toggleSideNav);
  const setFullscreen = useAppStore((state) => state.setFullscreen);
  const toggleDarkMode = useAppStore((state) => state.toggleDarkMode);
  const addAlert = useAppStore((state) => state.addAlert);
  const removeAlert = useAppStore((state) => state.removeAlert);
  const clearAlerts = useAppStore((state) => state.clearAlerts);
  const showModal = useAppStore((state) => state.showModal);
  const hideModal = useAppStore((state) => state.hideModal);
  const closeAllModals = useAppStore((state) => state.closeAllModals);
  const setSearch = useAppStore((state) => state.setSearch);
  const clearSearch = useAppStore((state) => state.clearSearch);
  const updateForm = useAppStore((state) => state.updateForm);
  const clearForm = useAppStore((state) => state.clearForm);
  const setCurrentProjectId = useAppStore((state) => state.setCurrentProjectId);
  const updateUserPreferences = useAppStore((state) => state.updateUserPreferences);
  const setBreadcrumbs = useAppStore((state) => state.setBreadcrumbs);

  // Custom app actions
  const setPageTitle = useAppStore((state) => state.setPageTitle);
  const showToast = useAppStore((state) => state.showToast);
  const hideToast = useAppStore((state) => state.hideToast);
  const addNotification = useAppStore((state) => state.addNotification);
  const removeNotification = useAppStore((state) => state.removeNotification);
  const clearNotifications = useAppStore((state) => state.clearNotifications);

  // Advanced actions
  const navigateWithBreadcrumb = useAppStore((state) => state.navigateWithBreadcrumb);
  const resetAppState = useAppStore((state) => state.resetAppState);
  const setUserPreferences = useAppStore((state) => state.setUserPreferences);

  // Convenience functions for toast notifications
  // These use sonner toast directly without adding to alerts to avoid duplicate notifications
  const showSuccess = useCallback(
    (message: string, description?: string) => {
      toast.success(message, {
        description,
      });
    },
    [],
  );

  const showError = useCallback(
    (message: string, description?: string) => {
      toast.error(message, {
        description,
      });
    },
    [],
  );

  const showWarning = useCallback(
    (message: string, description?: string) => {
      toast.warning(message, {
        description,
      });
    },
    [],
  );

  const showInfo = useCallback(
    (message: string, description?: string) => {
      toast.info(message, {
        description,
      });
    },
    [],
  );

  // Modal management helpers
  const showConfirmDialog = useCallback(
    (
      id: string,
      title: string,
      message: string,
      onConfirm: () => void,
      options?: {
        description?: string;
        confirmText?: string;
        cancelText?: string;
        variant?: "default" | "destructive";
      },
    ) => {
      showModal(id, {
        type: "confirm",
        title,
        message,
        data: {
          onConfirm,
          description: options?.description,
          confirmText: options?.confirmText ?? "Confirm",
          cancelText: options?.cancelText ?? "Cancel",
          variant: options?.variant ?? "default",
        },
      });
    },
    [showModal],
  );

  const showFormDialog = useCallback(
    (
      id: string,
      title: string,
      fields: unknown[],
      onSubmit: (data: Record<string, unknown>) => void,
      options?: {
        description?: string;
        submitText?: string;
        cancelText?: string;
        initialData?: unknown;
      },
    ) => {
      showModal(id, {
        type: "form",
        title,
        message: options?.description,
        data: {
          fields,
          onSubmit,
          submitText: options?.submitText ?? "Submit",
          cancelText: options?.cancelText ?? "Cancel",
          initialData: options?.initialData,
        },
      });
    },
    [showModal],
  );

  return {
    // Core state
    isLoading,
    isSideNavOpen,
    isFullscreen,
    isDarkMode,
    breadcrumbs,
    alerts,
    modals,
    search,
    forms,
    currentProjectId,
    userPreferences,

    // Navigation and UI actions
    setLoading,
    toggleSideNav,
    setFullscreen,
    toggleDarkMode,
    setPageTitle,
    setBreadcrumbs,
    setCurrentProjectId,

    // Alert management
    addAlert,
    removeAlert,
    clearAlerts,
    showSuccess,
    showError,
    showWarning,
    showInfo,

    // Modal management
    showModal,
    hideModal,
    closeAllModals,
    showConfirmDialog,
    showFormDialog,

    // Search management
    setSearch,
    clearSearch,

    // Form management
    updateForm,
    clearForm,

    // User preferences
    updateUserPreferences,

    // Advanced features
    navigateWithBreadcrumb,
    resetAppState,

    // Toast notifications
    showToast,
    hideToast,

    // Notifications
    addNotification,
    removeNotification,
    clearNotifications,

    // Store methods for advanced usage
    setUserPreferences,
  };
};

// ===========================================
// useLoading - Simplified loading state hook
// ===========================================

export const useLoading = () => {
  const { isLoading, setLoading } = useAppState();

  const startLoading = useCallback(
    (message?: string) => {
      setLoading({
        isLoading: true,
        message: message ?? "Loading...",
      });
    },
    [setLoading],
  );

  const stopLoading = useCallback(() => {
    setLoading({
      isLoading: false,
      message: "",
    });
  }, [setLoading]);

  const withLoading = useCallback(
    async <T>(
      asyncFunction: () => Promise<T>,
      loadingMessage?: string,
    ): Promise<T> => {
      try {
        startLoading(loadingMessage);
        const result = await asyncFunction();
        stopLoading();
        return result;
      } catch (error) {
        stopLoading();
        throw error;
      }
    },
    [startLoading, stopLoading],
  );

  return {
    isLoading,
    startLoading,
    stopLoading,
    withLoading,
  };
};

// ===========================================
// useModal - Modal management hook
// ===========================================

export const useModal = () => {
  const {
    modals,
    showModal,
    hideModal,
    closeAllModals,
    showConfirmDialog,
    showFormDialog,
  } = useAppState();

  const isModalOpen = useCallback(
    (id: string): boolean => {
      return modals.some((modal) => modal.id === id);
    },
    [modals],
  );

  const getModalData = useCallback(
    (id: string) => {
      return modals.find((modal) => modal.id === id);
    },
    [modals],
  );

  return {
    modals,
    isModalOpen,
    getModalData,
    showModal,
    hideModal,
    closeAllModals,
    showConfirmDialog,
    showFormDialog,
  };
};

// ===========================================
// useSearch - Search management hook
// ===========================================

export const useSearch = () => {
  const { search, setSearch, clearSearch } = useAppState();

  const updateSearchQuery = useCallback(
    (query: string) => {
      setSearch({ query, filters: {}, isActive: query.length > 0, isSearching: false });
    },
    [setSearch],
  );

  const updateSearchFilters = useCallback(
    (filters: Record<string, unknown>) => {
      setSearch({ ...search, filters, isActive: true });
    },
    [setSearch, search],
  );

  const resetSearch = useCallback(() => {
    clearSearch();
  }, [clearSearch]);

  return {
    searchQuery: search.query,
    searchFilters: search.filters,
    isSearchActive: search.isActive,
    isSearching: search.isSearching,
    updateSearchQuery,
    updateSearchFilters,
    resetSearch,
  };
};

// ===========================================
// useBreadcrumbs - Breadcrumb navigation hook
// ===========================================

export const useBreadcrumbs = () => {
  const { breadcrumbs, setBreadcrumbs, navigateWithBreadcrumb } = useAppState();

  const addBreadcrumb = useCallback(
    (item: { label: string; href?: string; icon?: React.ElementType }) => {
      const newBreadcrumbs = [...breadcrumbs, item];
      setBreadcrumbs(newBreadcrumbs);
      return navigateWithBreadcrumb(item);
    },
    [breadcrumbs, setBreadcrumbs, navigateWithBreadcrumb],
  );

  const removeBreadcrumb = useCallback(
    (index: number) => {
      const newBreadcrumbs = breadcrumbs.slice(0, index + 1);
      setBreadcrumbs(newBreadcrumbs);
    },
    [breadcrumbs, setBreadcrumbs],
  );

  const resetBreadcrumbs = useCallback(
    (home: { label: string; href: string; icon?: React.ElementType }) => {
      setBreadcrumbs([home]);
    },
    [setBreadcrumbs],
  );

  const updateBreadcrumb = useCallback(
    (
      index: number,
      item: {
        label: string;
        href?: string;
        icon?: React.ElementType;
      },
    ) => {
      const newBreadcrumbs = [...breadcrumbs];
      newBreadcrumbs[index] = item;
      setBreadcrumbs(newBreadcrumbs);
    },
    [breadcrumbs, setBreadcrumbs],
  );

  return {
    breadcrumbs,
    addBreadcrumb,
    removeBreadcrumb,
    resetBreadcrumbs,
    updateBreadcrumb,
    navigateWithBreadcrumb,
  };
};

// ===========================================
// useForm - Form state management hook
// ===========================================

export const useForm = (formId: string) => {
  const { forms, updateForm, clearForm } = useAppState();

  const formData = forms[formId]?.data ?? EMPTY_OBJECT;
  const formErrors = forms[formId]?.errors ?? EMPTY_OBJECT;
  const formTouched = forms[formId]?.touched ?? EMPTY_OBJECT;

  const updateField = useCallback(
    (field: string, value: unknown) => {
      updateForm(formId, {
        data: { ...formData, [field]: value },
        errors: { ...formErrors, [field]: undefined },
        touched: { ...formTouched, [field]: true },
      });
    },
    [formId, formData, formErrors, formTouched, updateForm],
  );

  const setFieldError = useCallback(
    (field: string, error: string) => {
      updateForm(formId, {
        data: formData,
        errors: { ...formErrors, [field]: error },
        touched: { ...formTouched, [field]: true },
      });
    },
    [formId, formData, formErrors, formTouched, updateForm],
  );

  const touchField = useCallback(
    (field: string) => {
      updateForm(formId, {
        data: formData,
        errors: formErrors,
        touched: { ...formTouched, [field]: true },
      });
    },
    [formId, formData, formErrors, formTouched, updateForm],
  );

  const validateField = useCallback(
    (field: string, validator: (value: unknown) => string | null) => {
      const error = validator((formData as Record<string, unknown>)[field]);
      setFieldError(field, error ?? "");
      return !error;
    },
    [formData, setFieldError],
  );

  const clearFormData = useCallback(() => {
    clearForm(formId);
  }, [clearForm, formId]);

  const isFieldTouched = useCallback(
    (field: string) => {
      return (formTouched as Record<string, boolean>)[field] ?? false;
    },
    [formTouched],
  );

  const getFieldError = useCallback(
    (field: string) => {
      return (formErrors as Record<string, string>)[field];
    },
    [formErrors],
  );

  return {
    formData,
    formErrors,
    formTouched,
    updateField,
    setFieldError,
    touchField,
    validateField,
    clearForm: clearFormData,
    isFieldTouched,
    getFieldError,
  };
};
