"use client";

import React, { memo } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Plus, FolderPlus, ClipboardList, Sparkles } from "lucide-react";
import Link from "next/link";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
  DropdownMenuSeparator,
} from "@/components/ui/dropdown-menu";

type DashboardHeaderProps = object;

const DashboardHeader = memo(function DashboardHeader(
  _props: DashboardHeaderProps,
) {
  return (
    <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
      <div>
        <h2 className="text-3xl font-bold tracking-tight text-foreground">
          Dashboard
        </h2>
        <p className="text-muted-foreground">
          Here's an overview of your projects and tasks.
        </p>
      </div>

      <div className="flex items-center gap-2 flex-wrap">
        {/* System Status Badge */}
        <Badge
          variant="outline"
          className="bg-emerald-500/10 text-emerald-500 border-emerald-500/20 px-3 py-1"
        >
          <span className="w-2 h-2 rounded-full bg-emerald-500 mr-2 animate-pulse" />{" "}
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
            className="w-56 bg-popover border-border"
          >
            <DropdownMenuItem
              asChild
              className="cursor-pointer focus:bg-accent"
            >
              <Link
                href="/projects?action=create"
                className="flex items-center"
              >
                <FolderPlus className="h-4 w-4 mr-3 text-blue-500" />
                <div>
                  <div className="font-medium text-foreground">New Project</div>
                  <div className="text-xs text-muted-foreground">
                    Create a new project
                  </div>
                </div>
              </Link>
            </DropdownMenuItem>

            <DropdownMenuItem
              asChild
              className="cursor-pointer focus:bg-accent"
            >
              <Link href="/projects?tab=tasks" className="flex items-center">
                <ClipboardList className="h-4 w-4 mr-3 text-emerald-500" />
                <div>
                  <div className="font-medium text-foreground">View Tasks</div>
                  <div className="text-xs text-muted-foreground">Manage your tasks</div>
                </div>
              </Link>
            </DropdownMenuItem>

            <DropdownMenuSeparator className="bg-border" />

            <DropdownMenuItem
              asChild
              className="cursor-pointer focus:bg-accent"
            >
              <Link href="/analytics" className="flex items-center">
                <Sparkles className="h-4 w-4 mr-3 text-violet-500" />
                <div>
                  <div className="font-medium text-foreground">View Analytics</div>
                  <div className="text-xs text-muted-foreground">Detailed insights</div>
                </div>
              </Link>
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </div>
  );
});

DashboardHeader.displayName = "DashboardHeader";

export { DashboardHeader };
