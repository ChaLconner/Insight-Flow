"use client";

import React, { memo, useCallback } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
    Plus,
    FolderPlus,
    ClipboardList,
    Sparkles
} from "lucide-react";
import Link from "next/link";
import {
    DropdownMenu,
    DropdownMenuContent,
    DropdownMenuItem,
    DropdownMenuTrigger,
    DropdownMenuSeparator,
} from "@/components/ui/dropdown-menu";

interface DashboardHeaderProps {
    onRefresh?: () => void;
    isRefetching?: boolean;
    lastUpdated?: Date | null;
}

const DashboardHeader = memo(function DashboardHeader({
    onRefresh,
    isRefetching = false,
    lastUpdated,
}: DashboardHeaderProps) {
    const handleRefresh = useCallback(() => {
        if (onRefresh && !isRefetching) {
            onRefresh();
        }
    }, [onRefresh, isRefetching]);

    // Format last updated time
    const formatLastUpdated = (date: Date | null | undefined): string => {
        if (!date) return '';
        const now = new Date();
        const diffMs = now.getTime() - date.getTime();
        const diffMins = Math.floor(diffMs / 60000);

        if (diffMins < 1) return 'Just now';
        if (diffMins < 60) return `${diffMins}m ago`;
        const diffHours = Math.floor(diffMins / 60);
        if (diffHours < 24) return `${diffHours}h ago`;
        return date.toLocaleDateString();
    };

    return (
        <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
            <div>
                <h2 className="text-3xl font-bold tracking-tight text-white">Dashboard</h2>
                <p className="text-zinc-400">
                    Here's an overview of your projects and tasks.
                    {lastUpdated && (
                        <span className="ml-2 text-zinc-500 text-sm">
                            Updated {formatLastUpdated(lastUpdated)}
                        </span>
                    )}
                </p>
            </div>

            <div className="flex items-center gap-2 flex-wrap">
                {/* System Status Badge */}
                <Badge
                    variant="outline"
                    className="bg-emerald-500/10 text-emerald-500 border-emerald-500/20 px-3 py-1"
                >
                    <span className="w-2 h-2 rounded-full bg-emerald-500 mr-2 animate-pulse" />
                    System Online
                </Badge>



                {/* Quick Actions Dropdown */}
                <DropdownMenu>
                    <DropdownMenuTrigger asChild>
                        <Button
                            size="sm"
                            className="bg-indigo-600 hover:bg-indigo-500 text-white cursor-pointer"
                        >
                            <Plus className="h-4 w-4 mr-2" />
                            Quick Actions
                        </Button>
                    </DropdownMenuTrigger>
                    <DropdownMenuContent
                        align="end"
                        className="w-56 bg-zinc-900 border-white/10"
                    >
                        <DropdownMenuItem asChild className="cursor-pointer focus:bg-white/10">
                            <Link href="/projects?action=create" className="flex items-center">
                                <FolderPlus className="h-4 w-4 mr-3 text-blue-400" />
                                <div>
                                    <div className="font-medium text-white">New Project</div>
                                    <div className="text-xs text-zinc-400">Create a new project</div>
                                </div>
                            </Link>
                        </DropdownMenuItem>

                        <DropdownMenuItem asChild className="cursor-pointer focus:bg-white/10">
                            <Link href="/tasks?action=create" className="flex items-center">
                                <ClipboardList className="h-4 w-4 mr-3 text-emerald-400" />
                                <div>
                                    <div className="font-medium text-white">New Task</div>
                                    <div className="text-xs text-zinc-400">Add a quick task</div>
                                </div>
                            </Link>
                        </DropdownMenuItem>

                        <DropdownMenuSeparator className="bg-white/10" />

                        <DropdownMenuItem asChild className="cursor-pointer focus:bg-white/10">
                            <Link href="/analytics" className="flex items-center">
                                <Sparkles className="h-4 w-4 mr-3 text-violet-400" />
                                <div>
                                    <div className="font-medium text-white">View Analytics</div>
                                    <div className="text-xs text-zinc-400">Detailed insights</div>
                                </div>
                            </Link>
                        </DropdownMenuItem>
                    </DropdownMenuContent>
                </DropdownMenu>
            </div>
        </div>
    );
});

DashboardHeader.displayName = 'DashboardHeader';

export { DashboardHeader };
export type { DashboardHeaderProps };
