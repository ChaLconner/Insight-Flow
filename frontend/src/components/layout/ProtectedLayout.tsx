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

// Loading component for authentication
function AuthLoadingLayout() {
    return (
        <div className="min-h-screen bg-black text-zinc-100 flex items-center justify-center">
            <div className="flex flex-col items-center space-y-4">
                <Loader2 className="h-8 w-8 animate-spin text-indigo-500" />
                <p className="text-zinc-400">Redirecting to login...</p>
            </div>
        </div>
    );
}

// Loading component for role-based redirects
function RoleRedirectLayout() {
    return (
        <div className="min-h-screen bg-black text-zinc-100 flex items-center justify-center">
            <div className="flex flex-col items-center space-y-4">
                <Loader2 className="h-8 w-8 animate-spin text-indigo-500" />
                <p className="text-zinc-400">Redirecting...</p>
            </div>
        </div>
    );
}

// Loading component for initial loading state
function InitialLoadingLayout() {
    return (
        <DashboardLayout>
            <div className="flex h-[calc(100vh-4rem)] items-center justify-center">
                <Loader2 className="h-8 w-8 animate-spin text-indigo-500" />
            </div>
        </DashboardLayout>
    );
}

export function ProtectedLayout({ children, requiredRole }: ProtectedLayoutProps) {
    // ALL HOOKS MUST BE CALLED AT THE TOP LEVEL - BEFORE ANY CONDITIONAL RETURNS
    const { isAuthenticated, isLoading, user } = useRequireAuth();
    const router = useRouter();
    const hasCheckedAuth = useRef(false);

    // Get role information from the same hook to avoid double initialization
    const isManagerOrHigher = user?.role === 'admin' || user?.role === 'manager';
    const isAdmin = user?.role === 'admin';

    // Check role-based access if required role is specified
    const hasRequiredAccess = !requiredRole ||
        (requiredRole === 'admin' && isAdmin) ||
        (requiredRole === 'manager' && isManagerOrHigher) ||
        (requiredRole && requiredRole !== 'admin' && requiredRole !== 'manager');

    // Fast role-based redirect with optimized checks
    useEffect(() => {
        // Skip checks if we don't have all required data yet
        if (!user || !requiredRole || !isAuthenticated) {return;}

        // Quick role check with early return
        if (!hasRequiredAccess) {
            // Prevent redirect loop if already on dashboard
            if (window.location.pathname !== '/dashboard') {
                console.log('🔒 ProtectedLayout: Redirecting for insufficient role access');
                router.push('/dashboard');
            }
        }
    }, [user, requiredRole, isAuthenticated, hasRequiredAccess, router]);

    // Mark that we've checked authentication at least once
    useEffect(() => {
        if (!isLoading && !hasCheckedAuth.current) {
            hasCheckedAuth.current = true;
        }
    }, [isLoading]);

    // Show loading spinner while checking authentication
    // CHANGED: Render DashboardLayout with a centered spinner instead of a full-screen blocking overlay
    // This improves UX by showing the app structure immediately
    if (isLoading) {
        return <InitialLoadingLayout />;
    }

    // If not authenticated, useRequireAuth will handle redirect
    // So we only render children if authenticated
    // Also check !user to avoid showing this screen when we have a user but isAuthenticated is briefly false
    if (!isAuthenticated && !user) {
        // Show loading state instead of null to prevent white screen
        return <AuthLoadingLayout />;
    }

    // If user doesn't have required role, show loading while redirecting
    if (requiredRole && !hasRequiredAccess) {
        return <RoleRedirectLayout />;
    }

    return (
        <DashboardLayout>
            {children}
        </DashboardLayout>
    );
}