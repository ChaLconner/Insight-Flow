// ===========================================
// useNotifications Hook
// ===========================================

import { useEffect, useCallback, useMemo, useRef } from 'react';
import { useNotificationStore, notificationSelectors, notificationActions } from '@/stores/notification-store';
import { NotificationType, NotificationPriority } from '@/types';
import { useTheme } from '@/hooks/use-theme';
import { notificationsApi } from '@/lib/api-endpoints';

// Primary notifications hook for managing in-app notifications
export const useNotifications = () => {
  // Zustand store state
  const store = useNotificationStore();

  // Selectors
  const notifications = notificationSelectors.getAllNotifications(store);
  const unreadCount = notificationSelectors.getUnreadCount(store);
  const isLoading = notificationSelectors.isLoading(store);
  const isConnected = notificationSelectors.isConnected(store);
  const filters = notificationSelectors.getFilters(store);
  const unreadNotifications = notificationSelectors.getUnreadNotifications(store);
  const readNotifications = notificationSelectors.getReadNotifications(store);
  const filteredNotifications = notificationSelectors.getFilteredNotifications(store);
  const notificationsByPriority = notificationSelectors.getNotificationsByPriority(store);
  const notificationsByType = notificationSelectors.getNotificationsByType(store);
  const latestNotifications = notificationSelectors.getLatestNotifications(store);

  // Actions
  const addNotification = store.addNotification;
  const setNotifications = store.setNotifications;
  const setUnreadCount = store.setUnreadCount;
  const markAsRead = store.markAsRead;
  const markAllAsRead = store.markAllAsRead;
  const removeNotification = store.removeNotification;
  const clearNotifications = store.clearNotifications;
  const clearReadNotifications = store.clearReadNotifications;
  const updateFilters = store.updateFilters;
  const resetFilters = store.resetFilters;
  const setLoading = store.setLoading;
  const setConnectionStatus = store.setConnectionStatus;

  // Real-time actions
  const connect = store.connect;
  const disconnect = store.disconnect;
  const reconnect = store.reconnect;

  // API Integration
  const fetchNotifications = useCallback(async () => {
    try {
      setLoading(true);
      const data = await notificationsApi.getNotifications();
      setNotifications(data);

      // Also update unread count to be accurate
      const count = await notificationsApi.getUnreadCount();
      setUnreadCount(count);
    } catch (error) {
      console.error("Failed to fetch notifications", error);
    } finally {
      setLoading(false);
    }
  }, [setNotifications, setUnreadCount, setLoading]);

  const fetchUnreadCount = useCallback(async () => {
    try {
      const count = await notificationsApi.getUnreadCount();
      // Only update if changed to avoid unnecessary re-renders or effects
      if (count !== unreadCount) {
        setUnreadCount(count);
        // If count changed, we might want to fetch the latest notifications too
        // But let's keep it separate for now or handle it in the polling logic
        return true; // Indicates change
      }
      return false;
    } catch (error) {
      console.error("Failed to fetch unread count", error);
      return false;
    }
  }, [unreadCount, setUnreadCount]);

  const markAsReadApi = useCallback(async (id: string) => {
    try {
      // Optimistic update
      markAsRead(id);
      await notificationsApi.markAsRead(id);
    } catch (error) {
      console.error("Failed to mark as read API", error);
      // Revert? For now, we assume success or eventual consistency
    }
  }, [markAsRead]);

  const markAllAsReadApi = useCallback(async () => {
    try {
      // Optimistic update
      markAllAsRead();
      await notificationsApi.markAllAsRead();
    } catch (error) {
      console.error("Failed to mark all as read API", error);
    }
  }, [markAllAsRead]);

  const deleteNotificationApi = useCallback(async (id: string) => {
    try {
      // Optimistic update
      removeNotification(id);
      await notificationsApi.deleteNotification(id);
    } catch (error) {
      console.error("Failed to delete notification API", error);
    }
  }, [removeNotification]);

  // Integration with console notifications (temporary replacement for toast)
  const showToastForNotification = useCallback((notification: any) => {

    if (typeof window !== 'undefined') {
      try {
        if ('Notification' in window && Notification.permission === 'granted') {
          new Notification(notification.title, {
            body: notification.message,
            icon: '/favicon.ico',
          });
        }
      } catch (error) {
        console.warn('Could not show notification:', error);
      }
    }
  }, []);

  // Helper functions for toast management
  const getToastDuration = useCallback((priority: string) => {
    switch (priority) {
      case 'low':
        return 3000;
      case 'medium':
        return 5000;
      case 'high':
        return 8000;
      case 'urgent':
        return 0; // Persistent
      default:
        return 5000;
    }
  }, []);

  const getToastAction = useCallback((
    notification: any,
    markAsRead: (id: string) => void
  ) => {
    if (notification.read) {
      return undefined;
    }

    return {
      label: 'Mark as Read',
      onClick: () => markAsRead(notification.id),
    };
  }, []);

  // CRUD operations with additional logic
  const createNotification = useCallback((
    title: string,
    message: string,
    options: {
      type?: string;
      priority?: string;
      duration?: number;
      action?: {
        label: string;
        handler: () => void;
      };
      data?: any;
      showToast?: boolean;
    } = {}
  ) => {
    const notification: any = {
      id: Date.now().toString() + Math.random().toString(36).substr(2, 9),
      userId: 'current-user', // This should come from auth context in real implementation
      title,
      message,
      type: options.type || NotificationType.SYSTEM,
      priority: options.priority || NotificationPriority.MEDIUM,
      read: false,
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
      data: options.data,
      actionUrl: undefined,
    };

    addNotification(notification);

    // Show toast if requested and not disabled
    if (options.showToast !== false) {
      showToastForNotification(notification);
    }

    return notification.id;
  }, [addNotification, showToastForNotification]);

  const showSuccess = useCallback((
    title: string,
    message?: string,
    options?: {
      priority?: string;
      action?: { label: string; handler: () => void };
      data?: any;
    }
  ) => {
    return createNotification(title, message || '', {
      type: NotificationType.SYSTEM,
      priority: options?.priority || NotificationPriority.MEDIUM,
      action: options?.action,
      data: options?.data,
    });
  }, [createNotification]);

  const showError = useCallback((
    title: string,
    message?: string,
    options?: {
      priority?: string;
      action?: { label: string; handler: () => void };
      data?: any;
      duration?: number;
    }
  ) => {
    return createNotification(title, message || '', {
      type: NotificationType.SYSTEM,
      priority: options?.priority || NotificationPriority.HIGH,
      action: options?.action,
      data: options?.data,
      showToast: options?.duration !== 0,
    });
  }, [createNotification]);

  const showWarning = useCallback((
    title: string,
    message?: string,
    options?: {
      priority?: string;
      action?: { label: string; handler: () => void };
      data?: any;
    }
  ) => {
    return createNotification(title, message || '', {
      type: NotificationType.SYSTEM,
      priority: options?.priority || NotificationPriority.MEDIUM,
      action: options?.action,
      data: options?.data,
    });
  }, [createNotification]);

  const showInfo = useCallback((
    title: string,
    message?: string,
    options?: {
      priority?: string;
      action?: { label: string; handler: () => void };
      data?: any;
    }
  ) => {
    return createNotification(title, message || '', {
      type: NotificationType.SYSTEM,
      priority: options?.priority || NotificationPriority.MEDIUM,
      action: options?.action,
      data: options?.data,
    });
  }, [createNotification]);

  // Bulk operations
  const markAsReadByType = useCallback((type: string) => {
    const typeNotifications = notificationsByType[type] || [];
    typeNotifications.forEach((notification: any) => {
      if (!notification.read) {
        markAsRead(notification.id);
      }
    });
  }, [notificationsByType, markAsRead]);

  const markAsReadByPriority = useCallback((priority: string) => {
    const priorityNotifications = notificationsByPriority[priority] || [];
    priorityNotifications.forEach((notification: any) => {
      if (!notification.read) {
        markAsRead(notification.id);
      }
    });
  }, [notificationsByPriority, markAsRead]);

  const removeByType = useCallback((type: string) => {
    const typeNotifications = notificationsByType[type] || [];
    typeNotifications.forEach((notification: any) => {
      removeNotification(notification.id);
    });
  }, [notificationsByType, removeNotification]);

  const removeByPriority = useCallback((priority: string) => {
    const priorityNotifications = notificationsByPriority[priority] || [];
    priorityNotifications.forEach((notification: any) => {
      removeNotification(notification.id);
    });
  }, [notificationsByPriority, removeNotification]);

  // Real-time connection management
  useEffect(() => {
    // Auto-connect when component mounts if not already connected
    if (!isConnected && notifications.length > 0) {
      connect();
    }

    // Cleanup on unmount
    return () => {
      // Don't auto-disconnect, let it persist
    };
  }, [isConnected, connect, notifications.length]);

  // Auto-remove old notifications based on retention policy
  useEffect(() => {
    const RETENTION_DAYS = 7; // Configurable retention period

    const cutoffTime = new Date();
    cutoffTime.setDate(cutoffTime.getDate() - RETENTION_DAYS);

    const oldNotifications = notifications.filter(
      (notification: any) => new Date(notification.createdAt) < cutoffTime
    );

    if (oldNotifications.length > 0) {
      oldNotifications.forEach((notification: any) => {
        removeNotification(notification.id);
      });
    }
  }, [notifications, removeNotification]);

  // Computed values
  const notificationStats = useMemo(() => {
    const stats = {
      total: notifications.length,
      unread: unreadCount,
      read: notifications.length - unreadCount,
      byType: {} as Record<string, number>,
      byPriority: {} as Record<string, number>,
    };

    // Count by type
    (['system', 'task_assigned', 'task_status_changed', 'task_due_date', 'project_invitation', 'project_update', 'mention', 'comment'] as string[]).forEach(type => {
      stats.byType[type] = notifications.filter((n: any) => n.type === type).length;
    });

    // Count by priority
    (['low', 'medium', 'high', 'urgent'] as string[]).forEach(priority => {
      stats.byPriority[priority] = notifications.filter((n: any) => n.priority === priority).length;
    });

    return stats;
  }, [notifications, unreadCount]);

  // Permission handling for browser notifications
  const requestNotificationPermission = useCallback(async () => {
    if (!('Notification' in window)) {
      console.warn('This browser does not support notifications');
      return false;
    }

    if (Notification.permission === 'granted') {
      return true;
    }

    if (Notification.permission === 'denied') {
      return false;
    }

    const permission = await Notification.requestPermission();
    return permission === 'granted';
  }, []);

  const showBrowserNotification = useCallback((
    title: string,
    options?: {
      body?: string;
      icon?: string;
      tag?: string;
      requireInteraction?: boolean;
    }
  ) => {
    if (Notification.permission !== 'granted') {
      return null;
    }

    const notification = new Notification(title, {
      body: options?.body,
      icon: options?.icon || '/favicon.ico',
      tag: options?.tag,
      requireInteraction: options?.requireInteraction,
    });

    return notification;
  }, []);

  return {
    // Core state
    notifications,
    unreadCount,
    isLoading,
    isConnected,
    filters,

    // Filtered views
    unreadNotifications,
    readNotifications,
    filteredNotifications,
    notificationsByPriority,
    notificationsByType,
    latestNotifications,

    // Statistics
    notificationStats,

    // CRUD operations
    createNotification,
    markAsRead: markAsReadApi, // Use API version
    markAllAsRead: markAllAsReadApi, // Use API version
    markAsReadByType,
    markAsReadByPriority,
    removeNotification: deleteNotificationApi, // Use API version
    clearNotifications,
    clearReadNotifications,
    removeByType,
    removeByPriority,

    // API Actions
    fetchNotifications,
    fetchUnreadCount,

    // Convenience methods
    showSuccess,
    showError,
    showWarning,
    showInfo,

    // Filter management
    updateFilters,
    resetFilters,

    // Real-time connection
    connect,
    disconnect,
    reconnect,
    setConnectionStatus,
    setLoading,

    // Browser notifications
    requestNotificationPermission,
    showBrowserNotification,

    // Integration
    showToastForNotification,

    // Store methods for advanced usage
    addNotification: store.addNotification,
  };
};

// ===========================================
// useUnreadNotifications - Simplified unread notifications hook
// ===========================================

export const useUnreadNotifications = () => {
  const {
    unreadNotifications,
    unreadCount,
    markAsRead,
    markAllAsRead
  } = useNotifications();

  const markAsReadById = useCallback((id: string) => {
    markAsRead(id);
  }, [markAsRead]);

  return {
    unreadNotifications,
    unreadCount,
    markAsRead: markAsReadById,
    markAllAsRead,
  };
};

// ===========================================
// useNotificationFilters - Notification filtering hook
// ===========================================

export const useNotificationFilters = () => {
  const { filters, updateFilters, resetFilters } = useNotifications();

  const setTypeFilter = useCallback((type: string | 'all') => {
    updateFilters({ type });
  }, [updateFilters]);

  const setPriorityFilter = useCallback((priority: string | 'all') => {
    updateFilters({ priority });
  }, [updateFilters]);

  const setReadFilter = useCallback((readStatus: 'all' | 'read' | 'unread') => {
    updateFilters({ readStatus });
  }, [updateFilters]);

  const setDateFilter = useCallback((dateRange: { start?: Date; end?: Date }) => {
    updateFilters({ dateRange });
  }, [updateFilters]);

  const setSearchFilter = useCallback((search: string) => {
    updateFilters({ search });
  }, [updateFilters]);

  const clearAllFilters = useCallback(() => {
    resetFilters();
  }, [resetFilters]);

  return {
    filters,
    setTypeFilter,
    setPriorityFilter,
    setReadFilter,
    setDateFilter,
    setSearchFilter,
    clearAllFilters,
    resetFilters,
  };
};

// ===========================================
// useRealTimeNotifications - Real-time notifications hook
// ===========================================

export const useRealTimeNotifications = () => {
  const {
    isConnected,
    connect,
    disconnect,
    reconnect,
    setConnectionStatus
  } = useNotifications();

  const connectionState = useMemo(() => {
    if (isConnected) { return 'connected'; }
    return 'disconnected';
  }, [isConnected]);

  return {
    isConnected,
    connectionState,
    connect,
    disconnect,
    reconnect,
    setConnectionStatus,
  };
};

// ===========================================
// useNotificationPolling - Polling hook
// ===========================================

export const useNotificationPolling = (intervalMs = 30000) => {
  const { fetchNotifications, fetchUnreadCount, unreadCount } = useNotifications();
  const prevUnreadCountRef = useRef(unreadCount);

  useEffect(() => {
    // Initial fetch
    fetchNotifications();

    let intervalId: ReturnType<typeof setInterval> | null = null;

    const startPolling = () => {
      if (intervalId) { return; }
      intervalId = setInterval(async () => {
        // Don't poll if document is hidden (bfcache/background tab optimization)
        if (document.visibilityState === 'hidden') { return; }

        const hasChanged = await fetchUnreadCount();
        if (hasChanged) {
          fetchNotifications();
        }
      }, intervalMs);
    };

    const stopPolling = () => {
      if (intervalId) {
        clearInterval(intervalId);
        intervalId = null;
      }
    };

    // Handle visibility change to suspend/resume polling
    const handleVisibilityChange = () => {
      if (document.visibilityState === 'visible') {
        fetchNotifications(); // Fetch immediately on resume
        startPolling();
      } else {
        stopPolling();
      }
    };

    // Start initial polling
    startPolling();

    document.addEventListener('visibilitychange', handleVisibilityChange);

    return () => {
      stopPolling();
      document.removeEventListener('visibilitychange', handleVisibilityChange);
    };
  }, [fetchNotifications, fetchUnreadCount, intervalMs]);
};

// ===========================================
// useNotificationSound - Sound notification utilities
// ===========================================

export const useNotificationSound = () => {
  const { currentTheme } = useTheme();

  const playNotificationSound = useCallback((type: string, priority: string = NotificationPriority.MEDIUM) => {
    // Create audio context for playing notification sounds
    try {
      const audioContext = new (window.AudioContext || (window as any).webkitAudioContext)();
      const oscillator = audioContext.createOscillator();
      const gainNode = audioContext.createGain();

      oscillator.connect(gainNode);
      gainNode.connect(audioContext.destination);

      // Configure sound based on type and priority
      let frequency = 800;
      let duration = 0.2;
      let volume = 0.1;

      switch (type) {
        case 'system':
          frequency = 900;
          duration = 0.15;
          break;
        case 'task_assigned':
          frequency = 1000;
          duration = 0.15;
          break;
        case 'comment':
          frequency = 800;
          duration = 0.2;
          break;
        default:
          frequency = 800;
          duration = 0.15;
          break;
      }

      // Adjust volume based on priority
      if (priority === 'urgent') {
        volume *= 1.5;
      } else if (priority === 'low') {
        volume *= 0.5;
      }

      // Reduce volume in quiet hours or based on theme preference
      const currentHour = new Date().getHours();
      const isQuietHours = currentHour >= 22 || currentHour <= 7;

      if (isQuietHours) {
        volume *= 0.3;
      }

      oscillator.frequency.setValueAtTime(frequency, audioContext.currentTime);
      oscillator.type = 'sine';

      gainNode.gain.setValueAtTime(volume, audioContext.currentTime);
      gainNode.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + duration);

      oscillator.start(audioContext.currentTime);
      oscillator.stop(audioContext.currentTime + duration);

      // Also try to play the file if available
      try {
        const audio = new Audio('/sounds/notification.mp3');
        audio.volume = volume;
        audio.play().catch(() => { });
      } catch (e) { }

    } catch (error) {
      console.warn('Failed to play notification sound:', error);
    }
  }, []);

  return {
    playNotificationSound,
  };
};