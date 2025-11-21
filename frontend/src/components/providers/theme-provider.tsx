// ===========================================
// Theme Provider Component
// ===========================================

'use client';

import { ReactNode, useEffect } from 'react';
import { useTheme } from '@/hooks/use-theme';
import { useIsHydrated } from '@/hooks/use-hydration';

interface ThemeProviderProps {
  children: ReactNode;
  defaultTheme?: 'light' | 'dark' | 'system';
  storageKey?: string;
}

export function ThemeProvider({
  children,
  defaultTheme = 'system',
  storageKey = 'insight-flow-theme',
}: ThemeProviderProps) {
  const { initializeTheme, syncWithStorage } = useTheme();
  const isHydrated = useIsHydrated();

  // Only run theme operations after hydration to prevent mismatch
  useEffect(() => {
    if (isHydrated) {
      // Initialize theme only once after hydration
      initializeTheme();
      // Sync with localStorage
      syncWithStorage();
    }
  }, [isHydrated, initializeTheme, syncWithStorage]);

  // Don't render anything until hydrated to prevent hydration mismatch
  if (!isHydrated) {
    return null;
  }

  return <>{children}</>;
}

export default ThemeProvider;