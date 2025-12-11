// ===========================================
// useAppState Hook
// ===========================================

import { useCallback, useEffect } from 'react';
import { useAppStore, appSelectors, appActions } from '@/stores/app-store';
import { toast } from 'sonner';

// Hook for app global state management
export const useAppState = () => {
  // Zustand store state
  const store = useAppStore();

  // Selectors
  const isLoading = appSelectors.isLoading(store);
  const isSideNavOpen = appSelectors.isSideNavOpen(store);
  const isFullscreen = appSelectors.isFullscreen(store);
  const isDarkMode = appSelectors.isDarkMode(store);
  const breadcrumbs = appSelectors.getBreadcrumbs(store);
  const alerts = appSelectors.getAlerts(store);
  const modals = appSelectors.getModals(store);
  const search = appSelectors.getSearch(store);
  const forms = appSelectors.getForms(store);
  const currentProjectId = appSelectors.getCurrentProjectId(store);
  const userPreferences = appSelectors.getUserPreferences(store);

  // Actions
  const setLoading = store.setLoading;
  const toggleSideNav = store.toggleSideNav;
  const setFullscreen = store.setFullscreen;
  const toggleDarkMode = store.toggleDarkMode;
  const addAlert = store.addAlert;
  const removeAlert = store.removeAlert;
  const clearAlerts = store.clearAlerts;
  const showModal = store.showModal;
  const hideModal = store.hideModal;
  const closeAllModals = store.closeAllModals;
  const setSearch = store.setSearch;
  const clearSearch = store.clearSearch;
  const updateForm = store.updateForm;
  const clearForm = store.clearForm;
  const setCurrentProjectId = store.setCurrentProjectId;
  const updateUserPreferences = store.updateUserPreferences;
  const setBreadcrumbs = store.setBreadcrumbs;

  // Custom app actions
  const setPageTitle = store.setPageTitle;
  const showToast = store.showToast;
  const hideToast = store.hideToast;
  const addNotification = store.addNotification;
  const removeNotification = store.removeNotification;
  const clearNotifications = store.clearNotifications;

  // Advanced actions
  const navigateWithBreadcrumb = store.navigateWithBreadcrumb;
  const resetAppState = store.resetAppState;

  // Convenience functions for toast notifications
  const showSuccess = useCallback((message: string, description?: string) => {
    toast.success(message, {
      description,
      action: {
        label: "Undo",
        onClick: () => { },
      },
    });
    addAlert({
      type: 'success',
      title: message,
      message: description ?? ''
    });
  }, [addAlert]);

  const showError = useCallback((message: string, description?: string) => {
    toast.error(message, {
      description,
      action: {
        label: "Retry",
        onClick: () => { },
      },
    });
    addAlert({
      type: 'error',
      title: message,
      message: description ?? ''
    });
  }, [addAlert]);

  const showWarning = useCallback((message: string, description?: string) => {
    toast.warning(message, {
      description,
    });
    addAlert({
      type: 'warning',
      title: message,
      message: description ?? ''
    });
  }, [addAlert]);

  const showInfo = useCallback((message: string, description?: string) => {
    toast.info(message, {
      description,
    });
    addAlert({
      type: 'info',
      title: message,
      message: description ?? ''
    });
  }, [addAlert]);

  // Modal management helpers
  const showConfirmDialog = useCallback((
    id: string,
    title: string,
    message: string,
    onConfirm: () => void,
    options?: {
      description?: string;
      confirmText?: string;
      cancelText?: string;
      variant?: 'default' | 'destructive';
    }
  ) => {
    showModal(id, {
      type: 'confirm',
      title,
      message,
      data: {
        onConfirm,
        description: options?.description,
        confirmText: options?.confirmText ?? 'Confirm',
        cancelText: options?.cancelText ?? 'Cancel',
        variant: options?.variant ?? 'default',
      },
    });
  }, [showModal]);

  const showFormDialog = useCallback((
    id: string,
    title: string,
    fields: any[],
    onSubmit: (data: any) => void,
    options?: {
      description?: string;
      submitText?: string;
      cancelText?: string;
      initialData?: any;
    }
  ) => {
    showModal(id, {
      type: 'form',
      title,
      message: options?.description,
      data: {
        fields,
        onSubmit,
        submitText: options?.submitText ?? 'Submit',
        cancelText: options?.cancelText ?? 'Cancel',
        initialData: options?.initialData,
      },
    });
  }, [showModal]);

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
    setUserPreferences: store.setUserPreferences,
  };
};

// ===========================================
// useLoading - Simplified loading state hook
// ===========================================

export const useLoading = () => {
  const { isLoading, setLoading } = useAppState();

  const startLoading = useCallback((message?: string) => {
    setLoading({
      isLoading: true,
      message: message ?? 'Loading...'
    });
  }, [setLoading]);

  const stopLoading = useCallback(() => {
    setLoading({
      isLoading: false,
      message: ''
    });
  }, [setLoading]);

  const withLoading = useCallback(async <T>(
    asyncFunction: () => Promise<T>,
    loadingMessage?: string
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
  }, [startLoading, stopLoading]);

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
    showFormDialog
  } = useAppState();

  const isModalOpen = useCallback((id: string): boolean => {
    return modals.some(modal => modal.id === id);
  }, [modals]);

  const getModalData = useCallback((id: string) => {
    return modals.find(modal => modal.id === id);
  }, [modals]);

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

  const updateSearchQuery = useCallback((query: string) => {
    setSearch({ query, filters: {}, isActive: query.length > 0 });
  }, [setSearch]);

  const updateSearchFilters = useCallback((filters: Record<string, any>) => {
    setSearch({ filters, isActive: true });
  }, [setSearch]);

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

  const addBreadcrumb = useCallback((item: {
    label: string;
    href?: string;
    icon?: any;
  }) => {
    const newBreadcrumbs = [...breadcrumbs, item];
    setBreadcrumbs(newBreadcrumbs);
    return navigateWithBreadcrumb(item);
  }, [breadcrumbs, setBreadcrumbs, navigateWithBreadcrumb]);

  const removeBreadcrumb = useCallback((index: number) => {
    const newBreadcrumbs = breadcrumbs.slice(0, index + 1);
    setBreadcrumbs(newBreadcrumbs);
  }, [breadcrumbs, setBreadcrumbs]);

  const resetBreadcrumbs = useCallback((home: {
    label: string;
    href: string;
    icon?: any;
  }) => {
    setBreadcrumbs([home]);
  }, [setBreadcrumbs]);

  const updateBreadcrumb = useCallback((index: number, item: {
    label: string;
    href?: string;
    icon?: any;
  }) => {
    const newBreadcrumbs = [...breadcrumbs];
    newBreadcrumbs[index] = item;
    setBreadcrumbs(newBreadcrumbs);
  }, [breadcrumbs, setBreadcrumbs]);

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

  const formData = forms[formId]?.data ?? {};
  const formErrors = forms[formId]?.errors ?? {};
  const formTouched = forms[formId]?.touched ?? {};

  const updateField = useCallback((field: string, value: any) => {
    updateForm(formId, {
      data: { ...formData, [field]: value },
      errors: { ...formErrors, [field]: undefined },
      touched: { ...formTouched, [field]: true },
    });
  }, [formId, formData, formErrors, formTouched, updateForm]);

  const setFieldError = useCallback((field: string, error: string) => {
    updateForm(formId, {
      data: formData,
      errors: { ...formErrors, [field]: error },
      touched: { ...formTouched, [field]: true },
    });
  }, [formId, formData, formErrors, formTouched, updateForm]);

  const touchField = useCallback((field: string) => {
    updateForm(formId, {
      data: formData,
      errors: formErrors,
      touched: { ...formTouched, [field]: true },
    });
  }, [formId, formData, formErrors, formTouched, updateForm]);

  const validateField = useCallback((field: string, validator: (value: any) => string | null) => {
    const error = validator(formData[field]);
    setFieldError(field, error ?? '');
    return !error;
  }, [formData, setFieldError]);

  const clearFormData = useCallback(() => {
    clearForm(formId);
  }, [clearForm, formId]);

  const isFieldTouched = useCallback((field: string) => {
    return formTouched[field] ?? false;
  }, [formTouched]);

  const getFieldError = useCallback((field: string) => {
    return formErrors[field];
  }, [formErrors]);

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