import type { User } from "@/types";
import { UserRole } from "@/types";

/**
 * User statistics data structure
 */
export interface UserStatsData {
    total: number;
    active: number;
    verified: number;
    admins: number;
    managers: number;
    members: number;
    viewers: number;
}

/**
 * Initial/default stats state
 */
export const DEFAULT_USER_STATS: UserStatsData = {
    total: 0,
    active: 0,
    verified: 0,
    admins: 0,
    managers: 0,
    members: 0,
    viewers: 0
};

/**
 * Filter state for user list
 */
export interface UserFiltersState {
    searchQuery: string;
    debouncedSearchQuery: string;
    roleFilter: UserRole | "all";
    statusFilter: "all" | "active" | "inactive";
}

/**
 * Pagination state for user list
 */
export interface UserPaginationState {
    page: number;
    pageSize: number;
    hasMore: boolean;
}

/**
 * Props for the UserCard component
 */
export interface UserCardProps {
    user: User;
    formatLastLogin: (dateString?: string) => string;
}

/**
 * Props for UserFilters component
 */
export interface UserFiltersProps {
    searchQuery: string;
    onSearchChange: (value: string) => void;
    debouncedSearchQuery: string;
    roleFilter: UserRole | "all";
    onRoleFilterChange: (value: UserRole | "all") => void;
    statusFilter: "all" | "active" | "inactive";
    onStatusFilterChange: (value: "all" | "active" | "inactive") => void;
    isLoading?: boolean;
    searchInputRef?: React.RefObject<HTMLInputElement>;
}

/**
 * Props for UserPagination component
 */
export interface UserPaginationProps {
    page: number;
    pageSize: number;
    totalUsers: number;
    currentCount: number;
    hasMore: boolean;
    isLoading: boolean;
    onPageChange: (page: number) => void;
}

/**
 * Props for UserStats component
 */
export interface UserStatsProps {
    stats: UserStatsData;
}

/**
 * Props for RoleDistribution component
 */
export interface RoleDistributionProps {
    stats: Pick<UserStatsData, 'admins' | 'managers' | 'members' | 'viewers'>;
}

/**
 * Keyboard shortcut configuration
 */
export const KEYBOARD_SHORTCUTS = {
    FOCUS_SEARCH: '/',
    REFRESH: 'r',
    NEXT_PAGE: 'ArrowRight',
    PREV_PAGE: 'ArrowLeft',
} as const;
