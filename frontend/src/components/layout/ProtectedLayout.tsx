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
        <div className="min-h-screen bg-black text-zinc-100 flex items-center justify-center relative overflow-hidden">
            {/* Background Gradients */}
            <div className="absolute inset-0 z-0 pointer-events-none">
                <div className="absolute -left-[10%] -top-[10%] h-[500px] w-[500px] rounded-full bg-indigo-500/10 blur-[100px]" />
                <div className="absolute -right-[10%] top-[20%] h-[500px] w-[500px] rounded-full bg-violet-500/10 blur-[100px]" />
                <div className="absolute bottom-[10%] left-[20%] h-[500px] w-[500px] rounded-full bg-blue-500/10 blur-[100px]" />
            </div>

            <div className="flex flex-col items-center space-y-4 z-10">
                <div className="relative">
                    <div className="absolute inset-0 bg-indigo-500/20 blur-xl rounded-full" />
                    <Loader2 className="h-8 w-8 animate-spin text-indigo-500 relative z-10" />
                </div>
                <p className="text-zinc-400 font-medium">Redirecting to login...</p>
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
        if (!user || !requiredRole || !isAuthenticated) { return; }

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

    // Show loading spinner while checking authentication (LCP Optimization)
    // Render DashboardLayout immediately with a spinner to show the "App Shell" ASAP
    if (isLoading) {
        return (
            <DashboardLayout>
                <div className="flex h-[calc(100vh-4rem)] w-full items-center justify-center">
                    <Loader2 className="h-8 w-8 animate-spin text-indigo-500" />
                </div>
            </DashboardLayout>
        );
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