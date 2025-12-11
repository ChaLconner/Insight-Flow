"use client";

import { forwardRef } from "react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { CustomSelect } from "@/components/ui/custom-select";
import { Search, Filter, RefreshCw, X } from "lucide-react";
import { UserRole } from "@/types";

interface UserFiltersProps {
    searchQuery: string;
    onSearchChange: (value: string) => void;
    debouncedSearchQuery: string;
    roleFilter: UserRole | "all";
    onRoleFilterChange: (value: UserRole | "all") => void;
    statusFilter: "all" | "active" | "inactive";
    onStatusFilterChange: (value: "all" | "active" | "inactive") => void;
    isLoading?: boolean;
}

const ROLE_OPTIONS = [
    { value: "all", label: "All Roles" },
    { value: UserRole.ADMIN, label: "Admin" },
    { value: UserRole.MANAGER, label: "Manager" },
    { value: UserRole.MEMBER, label: "Member" },
    { value: UserRole.VIEWER, label: "Viewer" },
];

const STATUS_OPTIONS = [
    { value: "all", label: "All Status" },
    { value: "active", label: "Active" },
    { value: "inactive", label: "Inactive" },
];

export const UserFilters = forwardRef<HTMLInputElement, UserFiltersProps>(
    function UserFilters(
        {
            searchQuery,
            onSearchChange,
            debouncedSearchQuery,
            roleFilter,
            onRoleFilterChange,
            statusFilter,
            onStatusFilterChange,
            isLoading = false,
        },
        ref
    ) {
        const isSearching = searchQuery !== debouncedSearchQuery || (isLoading && !!debouncedSearchQuery);

        const handleClearSearch = () => {
            onSearchChange("");
        };

        return (
            <div
                className="flex flex-col lg:flex-row gap-4"
                role="search"
                aria-label="Filter users"
            >
                <div className="relative flex-1">
                    <Search
                        className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-zinc-400"
                        aria-hidden="true"
                    />
                    <Input
                        ref={ref}
                        id="user-search"
                        name="user-search"
                        placeholder="Search users by name or email... (Press / to focus)"
                        value={searchQuery}
                        onChange={(e) => onSearchChange(e.target.value)}
                        className="pl-10 pr-10 bg-white/5 border-white/10 text-white placeholder:text-zinc-400"
                        aria-label="Search users by name or email. Press forward slash to focus."
                        aria-describedby="search-hint"
                    />
                    <span id="search-hint" className="sr-only">
                        Press forward slash key to focus this search field from anywhere on the page
                    </span>
                    {/* Loading/Clear indicator */}
                    <div className="absolute right-3 top-1/2 transform -translate-y-1/2">
                        {isSearching ? (
                            <RefreshCw
                                className="h-4 w-4 text-zinc-400 animate-spin"
                                aria-hidden="true"
                            />
                        ) : searchQuery ? (
                            <button
                                onClick={handleClearSearch}
                                className="text-zinc-400 hover:text-white transition-colors focus:outline-none focus:ring-2 focus:ring-indigo-500 rounded"
                                aria-label="Clear search"
                                type="button"
                            >
                                <X className="h-4 w-4" aria-hidden="true" />
                            </button>
                        ) : (
                            <kbd
                                className="hidden sm:inline-flex items-center px-1.5 py-0.5 text-xs text-zinc-500 bg-zinc-800 rounded border border-zinc-700"
                                aria-hidden="true"
                            >
                                /
                            </kbd>
                        )}
                    </div>
                </div>
                <div className="flex flex-col sm:flex-row gap-2" role="group" aria-label="Filter options">
                    <CustomSelect
                        value={roleFilter}
                        onChange={(value) => onRoleFilterChange(value as UserRole | "all")}
                        options={ROLE_OPTIONS}
                        className="w-full sm:w-[140px]"
                        aria-label="Filter by role"
                    />
                    <CustomSelect
                        value={statusFilter}
                        onChange={(value) => onStatusFilterChange(value as "all" | "active" | "inactive")}
                        options={STATUS_OPTIONS}
                        className="w-full sm:w-[140px]"
                        aria-label="Filter by status"
                    />
                    <Button
                        variant="outline"
                        className="glass border-white/10 text-white hover:bg-white/5"
                        aria-label="More filters"
                    >
                        <Filter className="h-4 w-4 mr-2" aria-hidden="true" />
                        More
                    </Button>
                </div>
            </div>
        );
    }
);

