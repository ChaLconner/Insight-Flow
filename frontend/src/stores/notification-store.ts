// ===========================================
// Zustand Notification Store
// ===========================================

import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type { Notification } from '@/types';

interface CustomNotification {
  id: string;
  userId: string;
  type: string;
  title: string;
  message: string;
  data?: Record<string, any>;
  read: boolean;
  actionUrl?: string;
  priority: string;
  expiresAt?: string;
  createdAt: string;
  updatedAt: string;
}

interface NotificationState {
  // State
  notifications: CustomNotification[];
  unreadCount: number;
  isPermissionGranted: boolean;
  pushEnabled: boolean;
  soundEnabled: boolean;
  vibrationEnabled: boolean;
  isLoading: boolean; // Add for compatibility
  isConnected: boolean; // Add for real-time
  filters: {
    type: string | 'all';
    priority: string | 'all';
    readStatus: 'all' | 'read' | 'unread';
    search: string;
    dateRange?: { start?: Date; end?: Date };
  }; // Add for compatibility
  
  // Actions
  addNotification: (notification: Omit<CustomNotification, 'id' | 'createdAt' | 'updatedAt'>) => void;
  markAsRead: (id: string) => void;
  markAllAsRead: () => void;
  removeNotification: (id: string) => void;
  clearAllNotifications: () => void;
  updateNotification: (id: string, updates: Partial<CustomNotification>) => void;
  
  // Settings Actions
  setPermissionGranted: (granted: boolean) => void;
  setPushEnabled: (enabled: boolean) => void;
  setSoundEnabled: (enabled: boolean) => void;
  setVibrationEnabled: (enabled: boolean) => void;
  
  // Loading and Connection
  setLoading: (loading: boolean) => void;
  setConnectionStatus: (connected: boolean) => void;
  
  // Filter Actions
  updateFilters: (filters: Partial<NotificationState['filters']>) => void;
  resetFilters: () => void;
  
  // Real-time Actions
  connect: () => void;
  disconnect: () => void;
  reconnect: () => void;
  
  // Utility Actions
  getNotificationsByType: (type: string) => CustomNotification[];
  getUnreadNotifications: () => CustomNotification[];
  getRecentNotifications: (limit?: number) => CustomNotification[];
  hasNotification: (id: string) => boolean;
  
  // Additional CRUD actions
  clearReadNotifications: () => void;
  
  // Aliases for compatibility
  clearNotifications: () => void; // Alias for clearAllNotifications
  
  // Private methods (must be implemented)
  showBrowserNotification: (notification: CustomNotification) => void;
  playNotificationSound: () => void;
}

export const useNotificationStore = create<NotificationState>()(
  persist(
    (set, get) => ({
      // Initial state
      notifications: [],
      unreadCount: 0,
      isPermissionGranted: false,
      pushEnabled: false,
      soundEnabled: true,
      vibrationEnabled: true,
      isLoading: false, // Add for compatibility
      isConnected: false, // Add for real-time
      filters: {
        type: 'all',
        priority: 'all',
        readStatus: 'all',
        search: '',
        dateRange: undefined,
      }, // Add for compatibility

      // Core Actions
      addNotification: (notificationData) => {
        const id = `notification-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
        const now = new Date().toISOString();
        
        const notification: CustomNotification = {
          ...notificationData,
          id,
          createdAt: now,
          updatedAt: now,
        };

        set((state) => ({
          notifications: [notification, ...state.notifications].slice(0, 100), // Keep only last 100
          unreadCount: notificationData.read ? state.unreadCount : state.unreadCount + 1,
        }));

        // Show browser notification if permission granted
        get().showBrowserNotification(notification);
        
        // Play sound if enabled
        if (get().soundEnabled) {
          get().playNotificationSound();
        }
        
        // Vibrate if enabled and on mobile
        if (get().vibrationEnabled && typeof navigator !== 'undefined' && navigator.vibrate) {
          navigator.vibrate([200, 100, 200]);
        }
      },

      markAsRead: (id) => {
        set((state) => {
          const notification = state.notifications.find(n => n.id === id);
          if (!notification || notification.read) {
            return state;
          }

          return {
            notifications: state.notifications.map(n =>
              n.id === id ? { ...n, read: true, updatedAt: new Date().toISOString() } : n
            ),
            unreadCount: Math.max(0, state.unreadCount - 1),
          };
        });
      },

      markAllAsRead: () => {
        set((state) => ({
          notifications: state.notifications.map(n => ({
            ...n,
            read: true,
            updatedAt: new Date().toISOString(),
          })),
          unreadCount: 0,
        }));
      },

      removeNotification: (id) => {
        set((state) => {
          const notification = state.notifications.find(n => n.id === id);
          const wasUnread = notification && !notification.read;

          return {
            notifications: state.notifications.filter(n => n.id !== id),
            unreadCount: wasUnread ? Math.max(0, state.unreadCount - 1) : state.unreadCount,
          };
        });
      },

      clearAllNotifications: () => {
        set({
          notifications: [],
          unreadCount: 0,
        });
      },

      updateNotification: (id, updates) => {
        set((state) => ({
          notifications: state.notifications.map(n =>
            n.id === id ? { ...n, ...updates, updatedAt: new Date().toISOString() } : n
          ),
        }));
      },

      // Settings Actions
      setPermissionGranted: (granted) => {
        set({ isPermissionGranted: granted });
      },

      setPushEnabled: (enabled) => {
        set({ pushEnabled: enabled });
      },

      setSoundEnabled: (enabled) => {
        set({ soundEnabled: enabled });
      },

      setVibrationEnabled: (enabled) => {
        set({ vibrationEnabled: enabled });
      },

      // Loading and Connection
      setLoading: (loading) => {
        set({ isLoading: loading });
      },

      setConnectionStatus: (connected) => {
        set({ isConnected: connected });
      },

      // Filter Actions
      updateFilters: (newFilters) => {
        set((state) => ({
          filters: { ...state.filters, ...newFilters }
        }));
      },

      resetFilters: () => {
        set({
          filters: {
            type: 'all',
            priority: 'all',
            readStatus: 'all',
            search: '',
            dateRange: undefined,
          }
        });
      },

      // Real-time Actions
      connect: () => {
        set({ isConnected: true });
        // In real implementation, this would establish WebSocket connection
      },

      disconnect: () => {
        set({ isConnected: false });
        // In real implementation, this would close WebSocket connection
      },

      reconnect: () => {
        get().disconnect();
        setTimeout(() => get().connect(), 1000);
      },

      // Utility Actions
      getNotificationsByType: (type) => {
        return get().notifications.filter(n => n.type === type);
      },

      getUnreadNotifications: () => {
        return get().notifications.filter(n => !n.read);
      },

      getRecentNotifications: (limit = 10) => {
        return get().notifications.slice(0, limit);
      },

      hasNotification: (id) => {
        return get().notifications.some(n => n.id === id);
      },

      // Additional CRUD actions
      clearReadNotifications: () => {
        set((state) => ({
          notifications: state.notifications.filter(n => !n.read),
          unreadCount: state.unreadCount, // Keep unread count unchanged
        }));
      },

      // Aliases for compatibility
      clearNotifications: () => {
        get().clearAllNotifications();
      },

      // Private methods
      showBrowserNotification: (notification: CustomNotification) => {
        if (!get().isPermissionGranted || !get().pushEnabled) {
          return;
        }

        if (typeof window !== 'undefined' && 'Notification' in window) {
          const browserNotification = new Notification(notification.title, {
            body: notification.message,
            icon: '/favicon.ico',
            badge: '/favicon.ico',
            tag: notification.id,
            requireInteraction: notification.priority === 'urgent',
          });

          browserNotification.onclick = () => {
            // Focus window and handle notification click
            window.focus();
            
            if (notification.actionUrl) {
              window.location.href = notification.actionUrl;
            }
            
            // Mark as read on click
            get().markAsRead(notification.id);
            
            // Close notification
            browserNotification.close();
          };

          // Auto-close after 5 seconds unless urgent
          if (notification.priority !== 'urgent') {
            setTimeout(() => {
              browserNotification.close();
            }, 5000);
          }
        }
      },

      playNotificationSound: () => {
        if (typeof window !== 'undefined') {
          try {
            const audio = new Audio('/sounds/notification.mp3');
            audio.volume = 0.5;
            audio.play().catch(error => {
              console.log('Could not play notification sound:', error);
            });
          } catch (error) {
            console.log('Notification sound not available:', error);
          }
        }
      },
    }),
    {
      name: 'insight-flow-notifications',
      partialize: (state) => ({
        notifications: state.notifications.slice(0, 50), // Persist only last 50
        soundEnabled: state.soundEnabled,
        vibrationEnabled: state.vibrationEnabled,
        pushEnabled: state.pushEnabled,
      }),
    }
  )
);

// ===========================================
// Notification Store Selectors
// ===========================================

export const notificationSelectors = {
  // Core selectors
  getNotifications: (state: NotificationState) => state.notifications,
  getAllNotifications: (state: NotificationState) => state.notifications, // Alias
  getUnreadCount: (state: NotificationState) => state.unreadCount,
  
  // Compatibility selectors
  isLoading: (state: NotificationState) => state.isLoading,
  isConnected: (state: NotificationState) => state.isConnected,
  getFilters: (state: NotificationState) => state.filters,
  
  // Filtered views
  getUnreadNotifications: (state: NotificationState) => state.notifications.filter(n => !n.read),
  getReadNotifications: (state: NotificationState) => state.notifications.filter(n => n.read),
  getFilteredNotifications: (state: NotificationState) => {
    // Apply current filters to notifications
    const { filters } = state;
    return state.notifications.filter(notification => {
      if (filters.type !== 'all' && notification.type !== filters.type) return false;
      if (filters.priority !== 'all' && notification.priority !== filters.priority) return false;
      if (filters.readStatus === 'read' && notification.read) return false;
      if (filters.readStatus === 'unread' && !notification.read) return false;
      if (filters.search && !notification.message.toLowerCase().includes(filters.search.toLowerCase())) return false;
      if (filters.dateRange) {
        const notificationDate = new Date(notification.createdAt);
        if (filters.dateRange.start && notificationDate < filters.dateRange.start) return false;
        if (filters.dateRange.end && notificationDate > filters.dateRange.end) return false;
      }
      return true;
    });
  },
  
  // Grouped views
  getNotificationsByPriority: (state: NotificationState) => {
    const grouped = {} as Record<string, CustomNotification[]>;
    state.notifications.forEach(notification => {
      if (!grouped[notification.priority]) {
        grouped[notification.priority] = [];
      }
      grouped[notification.priority].push(notification);
    });
    return grouped;
  },
  getNotificationsByType: (state: NotificationState) => {
    const grouped = {} as Record<string, CustomNotification[]>;
    state.notifications.forEach(notification => {
      if (!grouped[notification.type]) {
        grouped[notification.type] = [];
      }
      grouped[notification.type].push(notification);
    });
    return grouped;
  },
  
  // Latest notifications
  getLatestNotifications: (state: NotificationState) => (limit = 10) => 
    state.notifications.slice(0, limit) as CustomNotification[],
  
  // Settings
  getSettings: (state: NotificationState) => ({
    isPermissionGranted: state.isPermissionGranted,
    pushEnabled: state.pushEnabled,
    soundEnabled: state.soundEnabled,
    vibrationEnabled: state.vibrationEnabled,
  }),
  
  // Utility selectors
  hasUnread: (state: NotificationState) => state.unreadCount > 0,
  getUnread: (state: NotificationState) => state.notifications.filter(n => !n.read) as CustomNotification[], // Alias
  getRecent: (state: NotificationState) => {
    const twentyFourHoursAgo = new Date(Date.now() - 24 * 60 * 60 * 1000);
    return state.notifications.filter(n => 
      new Date(n.createdAt) > twentyFourHoursAgo
    );
  },
  getByType: (state: NotificationState) => (type: string) => 
    state.notifications.filter(n => n.type === type),
  getHighPriority: (state: NotificationState) => 
    state.notifications.filter(n => n.priority === 'urgent' || n.priority === 'high'),
} as const;

// ===========================================
// Notification Store Actions
// ===========================================

export const notificationActions = {
  // Request notification permission
  requestPermission: async (): Promise<boolean> => {
    if (typeof window === 'undefined' || !('Notification' in window)) {
      return false;
    }

    try {
      const permission = await Notification.requestPermission();
      const granted = permission === 'granted';
      
      useNotificationStore.getState().setPermissionGranted(granted);
      return granted;
    } catch (error) {
      console.error('Failed to request notification permission:', error);
      return false;
    }
  },

  // Show test notification
  showTestNotification: () => {
    const { addNotification } = useNotificationStore.getState();
    
    addNotification({
      userId: 'test',
      type: 'system',
      title: 'Test Notification',
      message: 'This is a test notification from Insight Flow',
      data: { test: true },
      read: false,
      priority: 'medium',
    });
  },

  // Handle notification click
  handleNotificationClick: (notification: CustomNotification) => {
    if (notification.actionUrl) {
      window.location.href = notification.actionUrl;
    }
    
    // Mark as read
    useNotificationStore.getState().markAsRead(notification.id);
  },

  // Filter notifications
  filterNotifications: (filters: {
    type?: string;
    priority?: string;
    read?: boolean;
    dateRange?: { start: Date; end: Date };
  }) => {
    const { notifications } = useNotificationStore.getState();
    
    return notifications.filter(notification => {
      if (filters.type && notification.type !== filters.type) {
        return false;
      }
      if (filters.priority && notification.priority !== filters.priority) {
        return false;
      }
      if (filters.read !== undefined && notification.read !== filters.read) {
        return false;
      }
      if (filters.dateRange) {
        const notificationDate = new Date(notification.createdAt);
        if (notificationDate < filters.dateRange.start || notificationDate > filters.dateRange.end) {
          return false;
        }
      }
      return true;
    });
  },

  // Bulk operations
  markMultipleAsRead: (ids: string[]) => {
    const { markAsRead } = useNotificationStore.getState();
    ids.forEach(id => markAsRead(id));
  },

  removeMultiple: (ids: string[]) => {
    const { removeNotification } = useNotificationStore.getState();
    ids.forEach(id => removeNotification(id));
  },
};

// ===========================================
// Auto-cleanup old notifications
// ===========================================

if (typeof window !== 'undefined') {
  // Clean up notifications older than 30 days every hour
  setInterval(() => {
    const { notifications } = useNotificationStore.getState();
    const thirtyDaysAgo = new Date(Date.now() - 30 * 24 * 60 * 60 * 1000);
    
    const oldNotifications = notifications.filter(n => 
      new Date(n.createdAt) < thirtyDaysAgo
    );
    
    if (oldNotifications.length > 0) {
      oldNotifications.forEach(notification => {
        useNotificationStore.getState().removeNotification(notification.id);
      });
    }
  }, 60 * 60 * 1000); // Every hour
}