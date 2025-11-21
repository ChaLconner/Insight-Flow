"use client";

import { Sidebar } from "./Sidebar";
import { Header } from "./Header";

interface DashboardLayoutProps {
    children: React.ReactNode;
}

export function DashboardLayout({ children }: DashboardLayoutProps) {
    return (
        <div className="min-h-screen bg-black text-zinc-100 selection:bg-indigo-500/30">
            {/* Background Gradients */}
            <div className="fixed inset-0 z-0 pointer-events-none">
                <div className="absolute -left-[10%] -top-[10%] h-[500px] w-[500px] rounded-full bg-indigo-500/10 blur-[100px]" />
                <div className="absolute -right-[10%] top-[20%] h-[500px] w-[500px] rounded-full bg-violet-500/10 blur-[100px]" />
                <div className="absolute bottom-[10%] left-[20%] h-[500px] w-[500px] rounded-full bg-blue-500/10 blur-[100px]" />
            </div>

            <Sidebar />

            <div className="relative pl-72">
                <Header />
                <main className="p-8">
                    <div className="mx-auto max-w-7xl animate-in fade-in slide-in-from-bottom-4 duration-700">
                        {children}
                    </div>
                </main>
            </div>
        </div>
    );
}
