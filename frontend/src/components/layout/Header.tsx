"use client";

import { useState, useEffect, useMemo } from "react";
import { usePathname } from "next/navigation";
import Image from "next/image";
import dynamic from "next/dynamic";
import { Bell, Search, User, Menu, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/hooks/use-auth-state";
import { GlobalSearch } from "./GlobalSearch";
import { cn, getAvatarUrl } from "@/lib/utils";

// Dynamic import to reduce initial bundle size (framer-motion is heavy)
const NotificationsPopover = dynamic(
  () =>
    import("./NotificationsPopover").then((mod) => mod.NotificationsPopover),
  {
    loading: () => (
      <Button
        variant="ghost"
        size="icon"
        className="relative h-10 w-10 rounded-full text-muted-foreground"
      >
        <Bell className="h-5 w-5" />
      </Button>
    ),
    ssr: false, // Notifications are client-side only anyway
  },
);

interface HeaderProps {
  onMenuClick: () => void;
}

export function Header({ onMenuClick }: Readonly<HeaderProps>) {
  const { user } = useAuth();
  const pathname = usePathname();
  const [isSearchOpen, setIsSearchOpen] = useState(false);
  const [isMounted, setIsMounted] = useState(false);

  // Prevent hydration mismatch by only rendering dynamic content after mount
  useEffect(() => {
    setIsMounted(true);
  }, []);

  const getPageTitle = (path: string) => {
    if (path === "/") {
      return "Dashboard";
    }
    if (path.startsWith("/projects")) {
      return "Projects";
    }
    if (path.startsWith("/tasks")) {
      return "Tasks";
    }
    if (path.startsWith("/analytics")) {
      return "Analytics";
    }
    if (path.startsWith("/users")) {
      return "Users";
    }
    if (path.startsWith("/settings")) {
      return "Settings";
    }
    return "Dashboard";
  };

  // Memoized greeting that only updates on client to prevent hydration mismatch
  const greeting = useMemo(() => {
    if (!isMounted) {
      return "Welcome"; // Static fallback for SSR
    }
    const hour = new Date().getHours();
    if (hour < 12) {
      return "Good morning";
    }
    if (hour < 18) {
      return "Good afternoon";
    }
    return "Good evening";
  }, [isMounted]);

  return (
    <header
      className={cn(
        "sticky top-0 z-40 flex h-20 w-full items-center justify-between bg-background/80 px-4 lg:px-8 backdrop-blur-xl backdrop-saturate-[1.8] transition-colors",
        !isSearchOpen && "border-b border-border",
      )}
    >
      {/* Mobile Search Overlay */}
      {isSearchOpen && (
        <div className="absolute inset-0 z-50 flex items-center bg-background/95 px-4 backdrop-blur-xl backdrop-saturate-[1.8] sm:hidden">
          <GlobalSearch
            className="w-full"
            onSelect={() => setIsSearchOpen(false)}
          />
          <Button
            variant="ghost"
            size="icon"
            className="ml-2 text-muted-foreground hover:text-foreground"
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
          aria-label="Open navigation menu"
          className="lg:hidden text-muted-foreground hover:text-foreground"
          onClick={onMenuClick}
        >
          <Menu className="h-6 w-6" />
        </Button>

        <div className="flex flex-col">
          <h1 className="text-xl font-semibold text-foreground tracking-tight">
            {getPageTitle(pathname)}
          </h1>
          <p className="text-sm text-muted-foreground hidden sm:block">
            {greeting},{" "}
            <span className="text-primary font-medium">
              {isMounted ? (user?.firstName ?? "User") : "User"}
            </span>
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
            className="text-muted-foreground hover:text-foreground"
            onClick={() => setIsSearchOpen(true)}
          >
            <Search className="h-5 w-5" />
          </Button>
        </div>

        {/* Notifications */}
        <NotificationsPopover />

        {/* User Profile */}
        <div className="flex items-center gap-3 border-l border-border pl-4">
          <div className="flex-col items-end hidden md:flex">
            <span className="text-sm font-medium text-foreground">
              {isMounted ? (user?.firstName ?? user?.email ?? "User") : "User"}
            </span>
            <span className="text-xs text-muted-foreground">
              {isMounted ? (user?.role ?? "User") : "User"}
            </span>
          </div>
          <Button
            variant="ghost"
            size="icon"
            className="h-10 w-10 rounded-full bg-secondary ring-1 ring-border hover:ring-primary/50 overflow-hidden p-0"
          >
            {isMounted && user?.avatar ? (
              <div className="relative h-full w-full">
                <Image
                  src={getAvatarUrl(user.avatar)}
                  alt={user.firstName ?? "User"}
                  fill
                  priority
                  className="object-cover"
                  sizes="40px"
                />
              </div>
            ) : (
              <User className="h-5 w-5 text-muted-foreground" />
            )}
          </Button>
        </div>
      </div>
    </header>
  );
}
