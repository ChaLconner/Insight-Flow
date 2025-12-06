"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import {
  LayoutDashboard,
  FolderKanban,

  Users,
  Settings,
  LogOut,
  Layers,
  BarChart3,
  User,
} from "lucide-react";
import { authActions } from "@/stores/auth-actions";

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

export function Sidebar({ isOpen, onClose }: { isOpen: boolean; onClose: () => void }) {
  const pathname = usePathname();

  return (
    <>
      {/* Mobile Backdrop */}
      {isOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/80 backdrop-blur-sm lg:hidden"
          onClick={onClose}
        />
      )}

      {/* Sidebar */}
      <aside
        className={cn(
          "fixed left-0 top-0 z-50 h-screen w-72 border-r border-white/10 bg-black/90 backdrop-blur-xl transition-transform duration-300 lg:translate-x-0 lg:bg-black/40",
          isOpen ? "translate-x-0" : "-translate-x-full"
        )}
      >
        <div className="flex h-full flex-col px-4 py-6">
          {/* Logo */}
          <div className="mb-10 flex items-center justify-between px-2">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-indigo-500 to-violet-600 shadow-lg shadow-indigo-500/20">
                <Layers className="h-6 w-6 text-white" />
              </div>
              <span className="text-xl font-bold tracking-tight text-white">
                Insight Flow
              </span>
            </div>
            {/* Close button for mobile */}
            <button
              onClick={onClose}
              aria-label="Close sidebar"
              className="rounded-lg p-2 text-zinc-400 hover:bg-white/5 hover:text-white lg:hidden"
            >
              <LogOut className="h-5 w-5 rotate-180" aria-hidden="true" />
            </button>
          </div>

          {/* Navigation */}
          <nav className="flex-1 space-y-2">
            {sidebarItems.map((item) => {
              const isActive = pathname === item.href;
              const Icon = item.icon;

              return (
                <Link
                  key={item.href}
                  href={item.href}
                  onClick={() => onClose()} // Close sidebar on navigation (mobile)
                  className={cn(
                    "group flex items-center gap-3 rounded-xl px-4 py-3 text-sm font-medium transition-all duration-200",
                    isActive
                      ? "bg-white/10 text-white shadow-inner shadow-white/5"
                      : "text-zinc-400 hover:bg-white/5 hover:text-white"
                  )}
                >
                  <Icon
                    className={cn(
                      "h-5 w-5 transition-colors",
                      isActive ? "text-indigo-400" : "text-zinc-500 group-hover:text-indigo-400"
                    )}
                  />
                  {item.title}
                </Link>
              );
            })}
          </nav>

          {/* User Profile / Footer */}
          <div className="mt-auto border-t border-white/10 pt-6">
            <button
              onClick={() => {
                const { logoutAndRedirect } = authActions;
                logoutAndRedirect('/auth/login');
              }}
              className="group flex w-full items-center gap-3 rounded-xl px-4 py-3 text-sm font-medium text-zinc-400 transition-all hover:bg-white/5 hover:text-white"
            >
              <LogOut className="h-5 w-5 text-zinc-500 transition-colors group-hover:text-red-400" />
              Sign Out
            </button>
          </div>
        </div>
      </aside>
    </>
  );
}
