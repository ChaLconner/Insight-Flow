"use client";

import { useState } from "react";
import { Sidebar } from "./Sidebar";
import { Header } from "./Header";
import { cn } from "@/lib/utils";

interface DashboardLayoutProps {
  children: React.ReactNode;
}

export function DashboardLayout({ children }: DashboardLayoutProps) {
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);

  return (
    <div className="min-h-screen bg-background text-foreground selection:bg-indigo-500/30">
      {/* Background Gradients */}
      <div className="fixed inset-0 z-0 pointer-events-none">
        <div className="absolute -left-[10%] -top-[10%] h-[500px] w-[500px] rounded-full bg-indigo-500/10 blur-[100px]" />
        <div className="absolute -right-[10%] top-[20%] h-[500px] w-[500px] rounded-full bg-violet-500/10 blur-[100px]" />
        <div className="absolute bottom-[10%] left-[20%] h-[500px] w-[500px] rounded-full bg-blue-500/10 blur-[100px]" />
      </div>

      <Sidebar isOpen={isSidebarOpen} onClose={() => setIsSidebarOpen(false)} />

      <div
        className={cn(
          "relative transition-all duration-300",
          "lg:pl-72", // Only add padding on large screens where sidebar is fixed
        )}
      >
        <Header onMenuClick={() => setIsSidebarOpen(true)} />
        <main className="p-4 md:p-8">
          <div className="mx-auto max-w-7xl animate-in fade-in slide-in-from-bottom-4 duration-700">
            {children}
          </div>
        </main>
      </div>
    </div>
  );
}
