"use client";

import { useRequireAuth } from "@/hooks/use-auth-state";
import { DashboardLayout } from "./DashboardLayout";
import { Loader2 } from "lucide-react";
import { useRouter } from "next/navigation";
import { useEffect, useRef } from "react";

interface ProtectedLayoutProps {
  children: React.ReactNode;
  requiredRole?: string; // Optional role requirement
}

/**
 * Note: Primary authentication check is now handled by middleware.ts at the Edge.
 * This component provides:
 * 1. Loading state while client-side auth initializes (hydration)
 * 2. Role-based access control (middleware only checks if logged in)
 * 3. Fallback protection if middleware is bypassed
 */

// Loading component for authentication - shown briefly during hydration
function AuthLoadingLayout() {
  return (
    <DashboardLayout>
      <div className="flex h-[calc(100vh-4rem)] w-full items-center justify-center">
        <div className="flex flex-col items-center space-y-4">
          <div className="relative">
            <div className="absolute inset-0 bg-indigo-500/20 blur-xl rounded-full" />
            <Loader2 className="h-8 w-8 animate-spin text-indigo-500 relative z-10" />
          </div>
          <p className="text-muted-foreground font-medium">Loading...</p>
        </div>
      </div>
    </DashboardLayout>
  );
}

// Loading component for role-based redirects
function RoleRedirectLayout() {
  return (
    <DashboardLayout>
      <div className="flex h-[calc(100vh-4rem)] w-full items-center justify-center">
        <div className="flex flex-col items-center space-y-4">
          <Loader2 className="h-8 w-8 animate-spin text-indigo-500" />
          <p className="text-muted-foreground">Redirecting...</p>
        </div>
      </div>
    </DashboardLayout>
  );
}

export function ProtectedLayout({
  children,
  requiredRole,
}: ProtectedLayoutProps) {
  // ALL HOOKS MUST BE CALLED AT THE TOP LEVEL - BEFORE ANY CONDITIONAL RETURNS
  const { isAuthenticated, isLoading, user } = useRequireAuth();
  const router = useRouter();
  const hasCheckedAuth = useRef(false);

  // Get role information from the same hook to avoid double initialization
  const isManagerOrHigher = user?.role === "admin" || user?.role === "manager";
  const isAdmin = user?.role === "admin";

  // Check role-based access if required role is specified
  const hasRequiredAccess =
    !requiredRole ||
    (requiredRole === "admin" && isAdmin) ||
    (requiredRole === "manager" && isManagerOrHigher) ||
    (requiredRole && requiredRole !== "admin" && requiredRole !== "manager");

  // Role-based redirect (auth redirect handled by middleware)
  useEffect(() => {
    // Skip checks if we don't have all required data yet
    if (!user || !requiredRole || !isAuthenticated) {
      return;
    }

    // Quick role check with early return
    if (!hasRequiredAccess) {
      // Prevent redirect loop if already on dashboard
      if (window.location.pathname !== "/dashboard") {
        router.push("/dashboard");
      }
    }
  }, [user, requiredRole, isAuthenticated, hasRequiredAccess, router]);

  // Mark that we've checked authentication at least once
  useEffect(() => {
    if (!isLoading && !hasCheckedAuth.current) {
      hasCheckedAuth.current = true;
    }
  }, [isLoading]);

  // Show App Shell immediately with loading indicator (LCP Optimization)
  // Middleware handles unauthenticated users, so this is just for hydration
  if (isLoading) {
    return (
      <DashboardLayout>
        <div className="flex h-[calc(100vh-4rem)] w-full items-center justify-center">
          <Loader2 className="h-8 w-8 animate-spin text-indigo-500" />
        </div>
      </DashboardLayout>
    );
  }

  // Fallback: If client-side auth check fails (middleware should have handled this)
  // Show loading state briefly - middleware will redirect on next navigation
  if (!isAuthenticated && !user) {
    return <AuthLoadingLayout />;
  }

  // If user doesn't have required role, show loading while redirecting
  if (requiredRole && !hasRequiredAccess) {
    return <RoleRedirectLayout />;
  }

  return <DashboardLayout>{children}</DashboardLayout>;
}
