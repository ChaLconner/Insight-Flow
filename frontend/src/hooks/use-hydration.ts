// ===========================================
// useIsHydrated Hook - Hydration Detection
// ===========================================

import { useEffect, useState } from 'react';

/**
 * Custom hook to detect if the component has been hydrated on the client
 * Prevents hydration mismatches by ensuring client-side operations only run after hydration
 */
export function useIsHydrated(): boolean {
  const [isHydrated, setIsHydrated] = useState(false);

  useEffect(() => {
    setIsHydrated(true);
  }, []);

  return isHydrated;
}

/**
 * Hook that returns whether we're in development mode
 */
export function useIsDevelopment(): boolean {
  const [isDev, setIsDev] = useState(false);

  useEffect(() => {
    setIsDev(
      typeof window !== 'undefined' && 
      (window.location.hostname === 'localhost' || 
       window.location.hostname === '127.0.0.1' ||
       process.env.NODE_ENV === 'development')
    );
  }, []);

  return isDev;
}

/**
 * Hook that returns whether we're running on the client
 */
export function useIsClient(): boolean {
  const [isClient, setIsClient] = useState(false);

  useEffect(() => {
    setIsClient(true);
  }, []);

  return isClient;
}

/**
 * Combined hook for hydration state
 */
export function useHydrationState() {
  const isHydrated = useIsHydrated();
  const isClient = useIsClient();
  const isDevelopment = useIsDevelopment();

  return {
    isHydrated,
    isClient,
    isDevelopment,
    isServer: !isClient,
  };
}