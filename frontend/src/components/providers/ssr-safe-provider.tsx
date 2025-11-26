'use client';

// ===========================================
// SSR-Safe Provider Components
// ===========================================

import { ReactNode, useState, useEffect } from 'react';
import { useTheme } from '@/hooks/use-theme';

// ===========================================
// Hydration Wrapper - Prevents mismatches
// ===========================================

interface HydrationWrapperProps {
  children: ReactNode;
}

export function HydrationWrapper({ children }: HydrationWrapperProps) {
  const [isHydrated, setIsHydrated] = useState(false);

  useEffect(() => {
    setIsHydrated(true);
  }, []);

  if (!isHydrated) {
    return null; // or a loading skeleton
  }

  return <>{children}</>;
}

// ===========================================
// Client-Only DevTools Wrapper
// ===========================================

interface DevtoolsWrapperProps {
  children: ReactNode;
}

export function DevtoolsWrapper({ children }: DevtoolsWrapperProps) {
  const [isDevelopment, setIsDevelopment] = useState(false);
  const [isClient, setIsClient] = useState(false);

  useEffect(() => {
    setIsClient(true);
    setIsDevelopment(
      typeof window !== 'undefined' && 
      (window.location.hostname === 'localhost' || 
       window.location.hostname === '127.0.0.1' ||
       process.env.NODE_ENV === 'development')
    );
  }, []);

  // If not running in development on the client, just render children.
  // We removed the React Query Devtools dependency to simplify the build.
  return <>{children}</>;
}

// ===========================================
// Theme-Aware Provider Wrapper
// ===========================================

interface ThemeAwareProviderProps {
  children: ReactNode;
  defaultTheme?: 'light' | 'dark' | 'system';
  storageKey?: string;
}

export function ThemeAwareProvider({ 
  children, 
  defaultTheme = 'system',
  storageKey = 'insight-flow-theme'
}: ThemeAwareProviderProps) {
  const [isHydrated, setIsHydrated] = useState(false);
  const { syncWithStorage, initializeTheme } = useTheme();

  useEffect(() => {
    setIsHydrated(true);
    // Initialize theme only on client
    initializeTheme();
    // Sync with storage
    syncWithStorage();
  }, [syncWithStorage, initializeTheme]);

  // Prevent hydration mismatch by not rendering theme-dependent content until hydrated
  if (!isHydrated) {
    return (
      <html lang="en" className="dark" suppressHydrationWarning>
        <body className="font-sans antialiased">
          {/* Minimal HTML to prevent hydration mismatch */}
        </body>
      </html>
    );
  }

  return <>{children}</>;
}

// ===========================================
// Safe Client-Side Only Component
// ===========================================

interface SafeClientOnlyProps {
  children: ReactNode;
  fallback?: ReactNode;
}

export function SafeClientOnly({ children, fallback = null }: SafeClientOnlyProps) {
  const [isClient, setIsClient] = useState(false);

  useEffect(() => {
    setIsClient(true);
  }, []);

  if (!isClient) {
    return <>{fallback}</>;
  }

  return <>{children}</>;
}

// ===========================================
// Query Provider with SSR Safety
// ===========================================

interface SSRQueryProviderProps {
  children: ReactNode;
}

export function SSRQueryProvider({ children }: SSRQueryProviderProps) {
  return (
    <HydrationWrapper>
      <DevtoolsWrapper>
        {children}
      </DevtoolsWrapper>
    </HydrationWrapper>
  );
}