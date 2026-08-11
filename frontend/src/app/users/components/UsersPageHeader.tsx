"use client";

import { Button } from "@/components/ui/button";
import { Plus, RefreshCw } from "lucide-react";

interface UsersPageHeaderProps {
  onRefresh: () => void;
  onInvite: () => void;
  isRefreshing: boolean;
}

/**
 * UsersPageHeader - Header section with title and action buttons
 */
export function UsersPageHeader({
  onRefresh,
  onInvite,
  isRefreshing,
}: Readonly<UsersPageHeaderProps>) {
  return (
    <header className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
      <div>
        <h1 className="text-3xl font-bold tracking-tight text-foreground">Users</h1>
        <p className="mt-1 text-muted-foreground">
          Manage team members and their permissions.
        </p>
      </div>
      <fieldset
        className="flex gap-2 w-full sm:w-auto"
      >
        <legend className="sr-only">Page actions</legend>
        <Button
          type="button"
          variant="outline"
          className="flex-1 sm:flex-none"
          onClick={onRefresh}
          disabled={isRefreshing}
          aria-label="Refresh users list"
        >
          <RefreshCw className={`h-4 w-4 mr-2 ${isRefreshing ? "animate-spin" : ""}`} aria-hidden="true" />
          Refresh
        </Button>
        <Button
          className="flex-1 sm:flex-none bg-indigo-600 hover:bg-indigo-500 text-white"
          onClick={onInvite}
          aria-label="Invite a new user"
        >
          <Plus className="h-4 w-4 mr-2" aria-hidden="true" />
          Invite User
        </Button>
      </fieldset>
    </header>
  );
}
