// ===========================================
// useRealTimeNotifications - Real-time notifications hook
// ===========================================

import { useMemo } from "react";
import { useNotifications } from "./use-notifications-core";

/**
 * Hook for managing real-time notification connections.
 */
export const useRealTimeNotifications = () => {
  const { isConnected, connect, disconnect, reconnect, setConnectionStatus } = useNotifications();

  const connectionState = useMemo(() => {
    return isConnected ? "connected" : "disconnected";
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
