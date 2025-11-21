"use client";

import { Bell, Search, User } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/hooks/use-auth-state";

export function Header() {
    const { user, isLoading } = useAuth();

    return (
        <header className="sticky top-0 z-30 flex h-20 w-full items-center justify-between border-b border-white/10 bg-black/40 px-8 backdrop-blur-xl">
            {/* Left: Page Title or Breadcrumbs */}
            <div>
                <h1 className="text-xl font-semibold text-white">Dashboard</h1>
                <p className="text-sm text-zinc-400">Welcome back, {user ? user.role : 'Team Leader'}</p>
            </div>

            {/* Right: Actions */}
            <div className="flex items-center gap-4">
                {/* Search */}
                <div className="relative hidden w-80 md:block">
                    <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-zinc-500" />
                    <Input
                        placeholder="Search projects, tasks..."
                        className="h-10 rounded-full border-white/10 bg-white/5 pl-10 text-sm text-white placeholder:text-zinc-500 focus:border-indigo-50/50 focus:bg-white/10 focus:ring-0"
                    />
                </div>

                {/* Notifications */}
                <Button
                    variant="ghost"
                    size="icon"
                    className="relative h-10 w-10 rounded-full text-zinc-400 hover:bg-white/10 hover:text-white"
                >
                    <Bell className="h-5 w-5" />
                    <span className="absolute right-2.5 top-2.5 h-2 w-2 rounded-full bg-indigo-500 ring-2 ring-black" />
                </Button>

                {/* User Profile */}
                <div className="flex items-center gap-3 border-l border-white/10 pl-4">
                    <div className="flex flex-col items-end hidden sm:flex">
                        <span className="text-sm font-medium text-white">{isLoading ? 'Loading...' : user?.firstName || user?.email || 'User'}</span>
                        <span className="text-xs text-zinc-400">{isLoading ? 'Loading...' : user?.role || 'Role'}</span>
                    </div>
                    <Button
                        variant="ghost"
                        size="icon"
                        className="h-10 w-10 rounded-full bg-gradient-to-br from-zinc-800 to-zinc-900 ring-1 ring-white/10 hover:ring-indigo-500/50"
                    >
                        <User className="h-5 w-5 text-zinc-400" />
                    </Button>
                </div>
            </div>
        </header>
    );
}
