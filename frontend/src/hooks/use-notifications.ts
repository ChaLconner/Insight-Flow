// ===========================================
// useNotifications Hook - Barrel Export
// ===========================================
// This file re-exports hooks from the notifications folder for backward compatibility.
// New imports should use '@/hooks/notifications' directly.

export {
  useNotifications,
  useUnreadNotifications,
  useNotificationFilters,
  useRealTimeNotifications,
  useNotificationPolling,
  useNotificationSound,
} from "./notifications";
