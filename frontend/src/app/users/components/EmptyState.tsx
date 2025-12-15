"use client";

import { Button } from "@/components/ui/button";
import { Search, Plus, UserPlus } from "lucide-react";
import type { UserRole } from "@/types";

interface EmptyStateProps {
  searchQuery: string;
  roleFilter: UserRole | "all";
  statusFilter: "all" | "active" | "inactive";
  onInviteClick: () => void;
}

/**
 * EmptyState - Shows when no users are found
 * Provides helpful message based on filter state
 */
export function EmptyState({
  searchQuery,
  roleFilter,
  statusFilter,
  onInviteClick,
}: EmptyStateProps) {
  const hasFilters =
    searchQuery || roleFilter !== "all" || statusFilter !== "all";

  return (
    <div
      className="text-center py-12"
      role="status"
      aria-label={
        hasFilters ? "No users match your filters" : "No users in team"
      }
    >
      <div
        className="mx-auto h-16 w-16 rounded-full bg-gradient-to-br from-indigo-500/20 to-purple-500/20 flex items-center justify-center mb-6"
        aria-hidden="true"
      >
        {hasFilters ? (
          <Search className="h-8 w-8 text-indigo-400" />
        ) : (
          <UserPlus className="h-8 w-8 text-indigo-400" />
        )}
      </div>

      <h3 className="text-xl font-semibold text-white mb-2">
        {hasFilters ? "No users found" : "No team members yet"}
      </h3>

      <p className="text-zinc-400 mb-6 max-w-md mx-auto">
        {hasFilters
          ? "Try adjusting your search or filter criteria to find the users you're looking for."
          : "Get started by inviting your first team member to collaborate on projects."}
      </p>

      {!hasFilters && (
        <Button
          className="bg-indigo-600 hover:bg-indigo-500 text-white"
          onClick={onInviteClick}
          aria-label="Invite your first team member"
        >
          <Plus className="h-4 w-4 mr-2" aria-hidden="true" />
          Invite First User
        </Button>
      )}

      {hasFilters && (
        <p className="text-sm text-zinc-500 mt-4">
          Tip: Press{" "}
          <kbd className="px-2 py-1 bg-zinc-800 rounded text-zinc-300 text-xs">
            /
          </kbd>{" "}
          to focus the search field
        </p>
      )}
    </div>
  );
}
