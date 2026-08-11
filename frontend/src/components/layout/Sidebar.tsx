"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import {
  LayoutDashboard,
  FolderKanban,
  Settings,
  LogOut,
  Layers,
  BarChart3,
  User,
} from "lucide-react";
import { authActions } from "@/stores/auth-actions";
import { useAuthStore } from "@/stores/auth-store";

function UserProfileDisplay() {
  const user = useAuthStore((state) => state.user);
  
  if (!user) {
    return null;
  }

  return (
    <div className="flex flex-col gap-0.5">
      <span className="font-semibold text-sm text-foreground truncate">
        {user.name ?? user.firstName}
      </span>
      <span className="text-xs text-muted-foreground truncate">
        {user.username ? `@${user.username}` : user.email}
      </span>
    </div>
  );
}

const sidebarItems = [
  {
    title: "Dashboard",
    href: "/dashboard",
    icon: LayoutDashboard,
  },
  {
    title: "Projects",
    href: "/projects",
    icon: FolderKanban,
  },

  {
    title: "Analytics",
    href: "/analytics",
    icon: BarChart3,
  },
  {
    title: "Users",
    href: "/users",
    icon: User,
  },
  {
    title: "Settings",
    href: "/settings",
    icon: Settings,
  },
];

export function Sidebar({
  isOpen,
  onClose,
}: Readonly<{
  isOpen: boolean;
  onClose: () => void;
}>) {
  const pathname = usePathname();

  return (
    <>
      {/* Mobile Backdrop */}
      {isOpen && (
        <button
          type="button"
          aria-label="Close navigation menu"
          className="fixed inset-0 z-40 bg-black/80 backdrop-blur-sm lg:hidden"
          onClick={onClose}
        />
      )}

      {/* Sidebar */}
      <aside
        className={cn(
          "fixed left-0 top-0 z-50 h-screen w-72 border-r border-border bg-card/95 backdrop-blur-xl transition-transform duration-300 lg:translate-x-0 lg:bg-card/80 [content-visibility:auto]",
          isOpen ? "translate-x-0" : "-translate-x-full",
        )}
      >
        <div className="flex h-full flex-col px-4 py-6">
          {/* Logo */}
          <div className="mb-10 flex items-center px-2">
            <Link
              href="/dashboard"
              onClick={() => onClose()}
              className="flex items-center gap-3"
            >
              <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-indigo-500 to-violet-600 shadow-lg shadow-indigo-500/20">
                <Layers className="h-6 w-6 text-white" />
              </div>
              <span className="text-xl font-bold tracking-tight text-foreground">
                Insight Flow
              </span>
            </Link>
          </div>

          {/* Navigation */}
          <nav className="flex-1 space-y-2">
            {sidebarItems.map((item) => {
              const isActive =
                pathname === item.href || pathname?.startsWith(`${item.href}/`);
              const Icon = item.icon;

              return (
                <Link
                  key={item.href}
                  href={item.href}
                  prefetch={true} // Prefetch pages for faster navigation
                  onClick={() => onClose()} // Close sidebar on navigation (mobile)
                  className={cn(
                    "group flex items-center gap-3 rounded-xl px-4 py-3 text-sm font-medium transition-all duration-200",
                    isActive
                      ? "bg-primary/25 text-primary shadow-sm font-semibold border border-primary/20"
                      : "text-muted-foreground hover:bg-white/10 hover:text-foreground hover:pl-5",
                  )}
                >
                  <Icon
                    className={cn(
                      "h-5 w-5 transition-colors",
                      isActive
                        ? "text-primary drop-shadow-sm"
                        : "text-muted-foreground group-hover:text-primary",
                    )}
                  />
                  {item.title}
                </Link>
              );
            })}
          </nav>

          {/* User Profile / Footer */}
          <div className="mt-auto border-t border-border pt-6">
             {/* User Info (Passive Discovery) */}
            <div className="mb-4 flex flex-col px-4">
               {/* We need to get user from store. Since Sidebar is client component, we can use useAuthStore */}
               <UserProfileDisplay />
            </div>

            <button
              type="button"
              aria-label="Sign out"
              onClick={() => {
                const { logoutAndRedirect } = authActions;
                logoutAndRedirect("/auth/login");
              }}
              className="group flex w-full items-center gap-3 rounded-xl px-4 py-3 text-sm font-medium text-muted-foreground transition-all hover:bg-accent hover:text-foreground cursor-pointer"
            >
              <LogOut className="h-5 w-5 text-muted-foreground transition-colors group-hover:text-destructive" />
              Sign Out
            </button>
          </div>
        </div>
      </aside>
    </>
  );
}
