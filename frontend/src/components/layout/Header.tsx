"use client";

import { useState, useEffect } from "react";
import { usePathname } from "next/navigation";
import { Bell, Search, User, Menu, X } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/hooks/use-auth-state";
import { GlobalSearch } from "./GlobalSearch";
import { NotificationsPopover } from "./NotificationsPopover";
import { cn, getAvatarUrl } from "@/lib/utils";

interface HeaderProps {
    onMenuClick: () => void;
}

export function Header({ onMenuClick }: HeaderProps) {
    const { user } = useAuth();
    const pathname = usePathname();
    const [isSearchOpen, setIsSearchOpen] = useState(false);

    // ตรวจสอบการอัปเดตข้อมูลผู้ใช้แบบ real-time
    useEffect(() => {
        if (user?.avatar) {
            console.log('🖼️ Header: Avatar updated to', getAvatarUrl(user.avatar));
        }
    }, [user?.avatar]);

    const getPageTitle = (path: string) => {
        if (path === '/') return 'Dashboard';
        if (path.startsWith('/projects')) return 'Projects';
        if (path.startsWith('/tasks')) return 'Tasks';
        if (path.startsWith('/analytics')) return 'Analytics';
        if (path.startsWith('/users')) return 'Team';
        if (path.startsWith('/settings')) return 'Settings';
        return 'Dashboard';
    };

    const getGreeting = () => {
        const hour = new Date().getHours();
        if (hour < 12) return 'Good morning';
        if (hour < 18) return 'Good afternoon';
        return 'Good evening';
    };

    return (
        <header className={cn(
            "sticky top-0 z-30 flex h-20 w-full items-center justify-between bg-black/40 px-4 lg:px-8 backdrop-blur-xl transition-colors",
            !isSearchOpen && "border-b border-white/10"
        )}>
            {/* Mobile Search Overlay */}
            {isSearchOpen && (
                <div className="absolute inset-0 z-50 flex items-center bg-zinc-950/95 px-4 backdrop-blur-xl sm:hidden">
                    <GlobalSearch
                        className="w-full"
                        onSelect={() => setIsSearchOpen(false)}
                    />
                    <Button
                        variant="ghost"
                        size="icon"
                        className="ml-2 text-zinc-400 hover:text-white"
                        onClick={() => setIsSearchOpen(false)}
                    >
                        <X className="h-5 w-5" />
                    </Button>
                </div>
            )}

            {/* Left: Menu Button & Page Title */}
            <div className="flex items-center gap-4">
                <Button
                    variant="ghost"
                    size="icon"
                    className="lg:hidden text-zinc-400 hover:text-white"
                    onClick={onMenuClick}
                >
                    <Menu className="h-6 w-6" />
                </Button>

                <div className="flex flex-col">
                    <h1 className="text-xl font-semibold bg-gradient-to-r from-white to-zinc-400 bg-clip-text text-transparent tracking-tight">
                        {getPageTitle(pathname)}
                    </h1>
                    <p className="text-sm text-zinc-400 hidden sm:block">
                        {getGreeting()}, <span className="text-indigo-400 font-medium">{user?.firstName || 'User'}</span>
                    </p>
                </div>
            </div>

            {/* Right: Actions */}
            <div className="flex items-center gap-2 sm:gap-4">
                {/* Search */}
                <div className="hidden sm:block">
                    <GlobalSearch />
                </div>
                <div className="sm:hidden">
                    <Button
                        variant="ghost"
                        size="icon"
                        className="text-zinc-400 hover:text-white"
                        onClick={() => setIsSearchOpen(true)}
                    >
                        <Search className="h-5 w-5" />
                    </Button>
                </div>

                {/* Notifications */}
                <NotificationsPopover />

                {/* User Profile */}
                <div className="flex items-center gap-3 border-l border-white/10 pl-4">
                    <div className="flex-col items-end hidden md:flex">
                        <span className="text-sm font-medium text-white">{user?.firstName || user?.email || 'User'}</span>
                        <span className="text-xs text-zinc-400">{user?.role || 'User'}</span>
                    </div>
                    <Button
                        variant="ghost"
                        size="icon"
                        className="h-10 w-10 rounded-full bg-gradient-to-br from-zinc-800 to-zinc-900 ring-1 ring-white/10 hover:ring-indigo-500/50 overflow-hidden p-0"
                    >
                        {user?.avatar ? (
                            <img
                                src={getAvatarUrl(user.avatar)}
                                alt={user.firstName || 'User'}
                                className="h-full w-full object-cover"
                                onError={(e) => {
                                    // Fallback to default avatar if image fails to load
                                    const target = e.target as HTMLImageElement;
                                    target.style.display = 'none';
                                    const parent = target.parentElement;
                                    if (parent) {
                                        const fallbackIcon = document.createElement('div');
                                        fallbackIcon.innerHTML = '<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="text-zinc-400"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path><circle cx="12" cy="7" r="4"></circle></svg>';
                                        fallbackIcon.className = 'flex items-center justify-center h-full w-full';
                                        parent.appendChild(fallbackIcon);
                                    }
                                }}
                            />
                        ) : (
                            <User className="h-5 w-5 text-zinc-400" />
                        )}
                    </Button>
                </div>
            </div>
        </header>
    );
}