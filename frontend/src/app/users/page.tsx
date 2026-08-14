"use client";

import { useEffect, useRef, useCallback, useState } from "react";
import dynamic from "next/dynamic";
import { ProtectedLayout } from "@/components/layout/ProtectedLayout";
import { Card, CardContent } from "@/components/ui/card";

const InviteUserModal = dynamic(
  () =>
    import("@/components/modals/InviteUserModal").then(
      (module) => module.InviteUserModal,
    ),
  {
    ssr: false,
    loading: () => null,
  },
);

// Local imports
import {
  UserCard,
  UserStats,
  UserFilters,
  UserPagination,
  RoleDistribution,
  UsersPageSkeleton,
  EmptyState,
  UsersPageHeader,
} from "./components";

import { useUsers } from "./hooks/useUsers";
import { formatLastLogin } from "@/lib/utils";

import { KEYBOARD_SHORTCUTS } from "./types";
import {
  blurEditableTargetOnEscape,
  useDocumentKeyDown,
} from "@/hooks/use-keyboard-shortcuts";

/**
 * UsersPage - Main page component for user management
 *
 * Features:
 * - Server-side pagination and filtering
 * - Debounced search
 * - Keyboard shortcuts (/ to focus search, r to refresh)
 * - Full accessibility support
 * - ARIA live regions for dynamic updates
 */
export default function UsersPage() {
  const [isInviteModalOpen, setIsInviteModalOpen] = useState(false);
  const searchInputRef = useRef<HTMLInputElement>(null);
  const announcerRef = useRef<HTMLDivElement>(null);

  // Use custom hook for all user management logic
  const {
    users,
    stats,
    loading,
    refreshing,
    error,
    dataFetched,
    searchQuery,
    setSearchQuery,
    debouncedSearchQuery,
    roleFilter,
    setRoleFilter,
    statusFilter,
    setStatusFilter,
    page,
    setPage,
    pageSize,
    hasMore,
    refresh,
    loadUsers,
  } = useUsers({ pageSize: 10, debounceMs: 300 });
  // Announce dynamic content changes to screen readers
  const announce = useCallback((message: string) => {
    if (announcerRef.current) {
      announcerRef.current.textContent = message;
    }
  }, []);

  // Announce user list updates
  useEffect(() => {
    if (!loading && dataFetched) {
      const message =
        users.length > 0
          ? `Showing ${users.length} users. Page ${page} of ${Math.ceil(stats.total / pageSize) || 1}.`
          : "No users found with current filters.";
      announce(message);
    }
  }, [
    users.length,
    loading,
    dataFetched,
    page,
    stats.total,
    pageSize,
    announce,
  ]);

  const handleKeyboardShortcut = useCallback(
    (event: KeyboardEvent) => {
      if (blurEditableTargetOnEscape(event)) {
        return;
      }

      switch (event.key) {
        case KEYBOARD_SHORTCUTS.FOCUS_SEARCH:
          event.preventDefault();
          searchInputRef.current?.focus();
          break;
        case KEYBOARD_SHORTCUTS.REFRESH:
          if (!event.ctrlKey && !event.metaKey) {
            event.preventDefault();
            refresh();
            announce("Refreshing user list");
          }
          break;
        case KEYBOARD_SHORTCUTS.NEXT_PAGE:
          if (hasMore && !loading) {
            event.preventDefault();
            setPage(page + 1);
          }
          break;
        case KEYBOARD_SHORTCUTS.PREV_PAGE:
          if (page > 1 && !loading) {
            event.preventDefault();
            setPage(page - 1);
          }
          break;
      }
    },
    [announce, hasMore, loading, page, refresh, setPage],
  );
  useDocumentKeyDown(handleKeyboardShortcut);

  const handleInviteClick = useCallback(() => {
    setIsInviteModalOpen(true);
  }, []);

  const handleInviteClose = useCallback(() => {
    setIsInviteModalOpen(false);
  }, []);

  const handleInviteSuccess = useCallback(() => {
    loadUsers(true);
    announce("User invited successfully. Refreshing list.");
  }, [loadUsers, announce]);

  // Loading state
  if (loading && !dataFetched) {
    return (
      <ProtectedLayout>
        <UsersPageSkeleton />
      </ProtectedLayout>
    );
  }

  // Error state
  if (error && !dataFetched) {
    return (
      <ProtectedLayout>
        <div
          className="flex flex-col items-center justify-center h-64 space-y-4"
          role="alert"
          aria-live="assertive"
        >
          <div className="text-red-400 text-center">
            <p className="text-lg font-medium">{error}</p>
            <button
              type="button"
              onClick={() => loadUsers(true)}
              className="mt-4 px-6 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg transition-colors focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2 focus:ring-offset-zinc-900"
              aria-label="Retry loading users"
            >
              Retry
            </button>
          </div>
        </div>
      </ProtectedLayout>
    );
  }

  return (
    <ProtectedLayout>
      {/* Skip to main content link */}
      <a
        href="#users-list"
        className="sr-only focus:not-sr-only focus:absolute focus:top-4 focus:left-4 focus:z-50 focus:px-4 focus:py-2 focus:bg-indigo-600 focus:text-white focus:rounded-lg"
      >
        Skip to users list
      </a>

      {/* Screen reader announcer for dynamic content */}
      <div
        ref={announcerRef}
        role="status"
        aria-live="polite"
        aria-atomic="true"
        className="sr-only"
      />

      {/* Keyboard shortcuts help (hidden, for screen readers) */}
      <div className="sr-only" aria-label="Keyboard shortcuts available">
        Press forward slash to focus search. Press R to refresh. Press left or
        right arrow keys to navigate pages. Press Escape to leave search field.
      </div>

      <div className="space-y-8">
        {/* Header */}
        <UsersPageHeader
          onRefresh={refresh}
          onInvite={handleInviteClick}
          isRefreshing={refreshing}
        />

        {error && dataFetched && (
          <div
            className="flex items-center justify-between gap-4 rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 text-red-200"
            role="alert"
            aria-live="assertive"
          >
            <span>{error}. Showing the last successful result.</span>
            <button
              type="button"
              onClick={() => loadUsers(true)}
              className="shrink-0 rounded-md border border-red-300/40 px-3 py-1 text-sm hover:bg-red-500/20 focus:outline-none focus:ring-2 focus:ring-red-400"
            >
              Retry
            </button>
          </div>
        )}

        {/* Stats Grid */}
        <section aria-label="User statistics">
          <UserStats stats={stats} />
        </section>

        {/* Search and Filter */}
        <section aria-label="User filters">
          <UserFilters
            ref={searchInputRef}
            searchQuery={searchQuery}
            onSearchChange={setSearchQuery}
            debouncedSearchQuery={debouncedSearchQuery}
            roleFilter={roleFilter}
            onRoleFilterChange={setRoleFilter}
            statusFilter={statusFilter}
            onStatusFilterChange={setStatusFilter}
            isLoading={loading}
          />
        </section>

        {/* Users List */}
        <section id="users-list" aria-label="Users list" aria-busy={loading}>
          {users.length > 0 ? (
            <Card className="border-border bg-card backdrop-blur-sm">
              <CardContent className="p-0">
                <ul className="divide-y divide-border">
                  {users.map((user) => (
                    <li key={user.id}>
                      <UserCard user={user} formatLastLogin={formatLastLogin} />
                    </li>
                  ))}
                </ul>

                {/* Pagination Controls */}
                <UserPagination
                  page={page}
                  pageSize={pageSize}
                  totalUsers={stats.total}
                  currentCount={users.length}
                  hasMore={hasMore}
                  isLoading={loading}
                  onPageChange={setPage}
                />
              </CardContent>
            </Card>
          ) : (
            !loading && (
              <EmptyState
                searchQuery={searchQuery}
                roleFilter={roleFilter}
                statusFilter={statusFilter}
                onInviteClick={handleInviteClick}
              />
            )
          )}
        </section>

        {/* Role Distribution */}
        {stats.total > 0 && (
          <section aria-label="Role distribution">
            <RoleDistribution stats={stats} />
          </section>
        )}
      </div>

      {/* Invite User Modal */}
      <InviteUserModal
        isOpen={isInviteModalOpen}
        onClose={handleInviteClose}
        onSuccess={handleInviteSuccess}
      />
    </ProtectedLayout>
  );
}
