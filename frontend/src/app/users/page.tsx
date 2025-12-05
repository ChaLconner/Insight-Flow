"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { DashboardLayout } from "@/components/layout/DashboardLayout";
import { ProtectedLayout } from "@/components/layout/ProtectedLayout";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import {
  Search,
  Filter,
  Plus,
  MoreHorizontal,
  Mail,
  Phone,
  MapPin,
  Calendar,
  Shield,
  UserCheck,
  UserX,
  Edit,
  Trash2,
  MailIcon,
  MoreVertical,
  Users as UsersIcon,
  Activity,
  Crown,
  User,
  RefreshCw
} from "lucide-react";
import { Skeleton } from "@/components/ui/skeleton";
import type { User as UserType } from "@/types";
import { UserRole } from "@/types";
import { useAuthStore } from "@/stores/auth-store";
import { usersApi } from "@/lib/api-endpoints";
import { CustomSelect } from "@/components/ui/custom-select";
import { getAvatarUrl } from "@/lib/utils";

export default function UsersPage() {
  const [users, setUsers] = useState<UserType[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [roleFilter, setRoleFilter] = useState<UserRole | "all">("all");
  const [statusFilter, setStatusFilter] = useState<"all" | "active" | "inactive">("all");

  const { accessToken, isAuthenticated, isLoading } = useAuthStore();
  const [dataFetched, setDataFetched] = useState(false);

  // Refs to prevent duplicate API calls
  const isLoadingRef = useRef(false);
  const lastLoadTime = useRef<number>(0);

  const loadUsers = useCallback(async (forceRefresh = false) => {
    if (!accessToken) { return; }

    // Rate limiting: prevent calls within 2 seconds of each other
    const now = Date.now();
    if (!forceRefresh && now - lastLoadTime.current < 2000 && dataFetched) {
      console.log('Rate limiting: skipping loadUsers call');
      return;
    }

    // Prevent duplicate concurrent calls
    if (isLoadingRef.current) {
      console.log('Already loading users, skipping duplicate call');
      return;
    }

    try {
      isLoadingRef.current = true;
      lastLoadTime.current = now;

      if (forceRefresh) {
        setRefreshing(true);
      } else {
        setLoading(true);
      }
      setError(null);

      // Try to fetch users from API
      try {
        const response = await usersApi.searchUsers("");
        const userList = Array.isArray(response) ? response : (response as any).data || [];
        setUsers(userList);
      } catch (apiError) {
        console.log('API not available, using empty array');
        // Keep empty array if API is not available
        setUsers([]);
      }

      setDataFetched(true);
    } catch (err) {
      console.error('Error loading users:', err);
      setError('Failed to load users');
    } finally {
      isLoadingRef.current = false;
      setLoading(false);
      setRefreshing(false);
    }
  }, [accessToken, dataFetched]);

  useEffect(() => {
    // Fast path: Skip if we're still loading or already have data
    if (isLoading || dataFetched) { return; }

    if (isAuthenticated && accessToken) {
      loadUsers();
    } else if (!isAuthenticated) {
      setLoading(false);
    }
  }, [isAuthenticated, accessToken, isLoading, dataFetched, loadUsers]);

  const handleRefresh = () => {
    loadUsers(true);
  };

  const filteredUsers = users.filter(user => {
    const matchesSearch = user.firstName?.toLowerCase().includes(searchQuery.toLowerCase()) ||
      user.lastName?.toLowerCase().includes(searchQuery.toLowerCase()) ||
      user.email.toLowerCase().includes(searchQuery.toLowerCase()) ||
      user.username.toLowerCase().includes(searchQuery.toLowerCase());

    const matchesRole = roleFilter === "all" || user.role === roleFilter;
    const matchesStatus = statusFilter === "all" ||
      (statusFilter === "active" && user.isActive) ||
      (statusFilter === "inactive" && !user.isActive);

    return matchesSearch && matchesRole && matchesStatus;
  });

  const getRoleBadge = (role: UserRole) => {
    const roleConfig = {
      [UserRole.ADMIN]: {
        label: "Admin",
        color: "bg-purple-500/20 text-purple-400",
        icon: <Crown className="h-3 w-3 mr-1" />
      },
      [UserRole.MANAGER]: {
        label: "Manager",
        color: "bg-blue-500/20 text-blue-400",
        icon: <Shield className="h-3 w-3 mr-1" />
      },
      [UserRole.MEMBER]: {
        label: "Member",
        color: "bg-emerald-500/20 text-emerald-400",
        icon: <User className="h-3 w-3 mr-1" />
      },
      [UserRole.VIEWER]: {
        label: "Viewer",
        color: "bg-zinc-500/20 text-zinc-400",
        icon: <User className="h-3 w-3 mr-1" />
      }
    };

    const config = roleConfig[role];

    if (!config) {
      return (
        <Badge className="bg-zinc-500/20 text-zinc-400">
          <User className="h-3 w-3 mr-1" />
          {role || "Unknown"}
        </Badge>
      );
    }

    return (
      <Badge className={config?.color || "bg-zinc-500/20 text-zinc-400"}>
        {config?.icon}
        {config?.label || role}
      </Badge>
    );
  };

  const getStatusBadge = (user: UserType) => {
    if (!user.isActive) {
      return (
        <Badge className="bg-red-500/20 text-red-400">
          <UserX className="h-3 w-3 mr-1" />
          Inactive
        </Badge>
      );
    }

    if (!user.emailVerified) {
      return (
        <Badge className="bg-amber-500/20 text-amber-400">
          <MailIcon className="h-3 w-3 mr-1" />
          Unverified
        </Badge>
      );
    }

    return (
      <Badge className="bg-emerald-500/20 text-emerald-400">
        <UserCheck className="h-3 w-3 mr-1" />
        Active
      </Badge>
    );
  };

  const formatDate = (dateString?: string) => {
    if (!dateString) {
      return "Never";
    }
    return new Date(dateString).toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric"
    });
  };

  const formatLastLogin = (dateString?: string) => {
    if (!dateString) {
      return "Never logged in";
    }

    const date = new Date(dateString);
    const now = new Date();
    const diffInHours = Math.floor((now.getTime() - date.getTime()) / (1000 * 60 * 60));

    if (diffInHours < 1) {
      return "Just now";
    }
    if (diffInHours < 24) {
      return `${diffInHours}h ago`;
    }

    const diffInDays = Math.floor(diffInHours / 24);
    if (diffInDays === 1) {
      return "Yesterday";
    }
    if (diffInDays < 7) {
      return `${diffInDays}d ago`;
    }

    return formatDate(dateString);
  };

  // Calculate user statistics
  const stats = {
    total: users.length,
    active: users.filter(u => u.isActive).length,
    verified: users.filter(u => u.emailVerified).length,
    admins: users.filter(u => u.role === UserRole.ADMIN).length,
    managers: users.filter(u => u.role === UserRole.MANAGER).length,
    members: users.filter(u => u.role === UserRole.MEMBER).length,
    viewers: users.filter(u => u.role === UserRole.VIEWER).length,
  };

  if (loading) {
    return (
      <ProtectedLayout>
        <div className="space-y-8">
          {/* Header Skeleton */}
          <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
            <div className="space-y-2">
              <Skeleton className="h-8 w-48" />
              <Skeleton className="h-4 w-64" />
            </div>
            <div className="flex gap-2 w-full sm:w-auto">
              <Skeleton className="h-10 w-24" />
              <Skeleton className="h-10 w-32" />
            </div>
          </div>

          {/* Stats Grid Skeleton */}
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
            {[...Array(4)].map((_, i) => (
              <Card key={i} className="border-white/10 bg-white/5 backdrop-blur-sm">
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                  <Skeleton className="h-4 w-24" />
                  <Skeleton className="h-4 w-4" />
                </CardHeader>
                <CardContent>
                  <Skeleton className="h-8 w-16 mb-2" />
                  <Skeleton className="h-3 w-32" />
                </CardContent>
              </Card>
            ))}
          </div>

          {/* Search and Filter Skeleton */}
          <div className="flex flex-col lg:flex-row gap-4">
            <Skeleton className="h-10 flex-1" />
            <div className="flex flex-col sm:flex-row gap-2">
              <Skeleton className="h-10 w-32" />
              <Skeleton className="h-10 w-32" />
              <Skeleton className="h-10 w-20" />
            </div>
          </div>

          {/* Users List Skeleton */}
          <Card className="border-white/10 bg-white/5 backdrop-blur-sm">
            <CardContent className="p-0">
              <div className="divide-y divide-white/10">
                {[...Array(5)].map((_, i) => (
                  <div key={i} className="p-6">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-4">
                        <Skeleton className="h-12 w-12 rounded-full" />
                        <div className="space-y-2">
                          <div className="flex items-center gap-3">
                            <Skeleton className="h-5 w-32" />
                            <Skeleton className="h-5 w-20 rounded-full" />
                            <Skeleton className="h-5 w-20 rounded-full" />
                          </div>
                          <div className="flex items-center gap-4">
                            <Skeleton className="h-4 w-48" />
                            <Skeleton className="h-4 w-32" />
                            <Skeleton className="h-4 w-32" />
                          </div>
                        </div>
                      </div>
                      <div className="flex items-center gap-2">
                        <Skeleton className="h-8 w-16" />
                        <Skeleton className="h-8 w-24" />
                        <Skeleton className="h-8 w-8" />
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </div>
      </ProtectedLayout>
    );
  }

  if (error && !dataFetched) {
    return (
      <ProtectedLayout>
        <div className="flex flex-col items-center justify-center h-64 space-y-4">
          <div className="text-red-400 text-center">
            <p className="text-lg font-medium">{error}</p>
            <button
              onClick={() => loadUsers()}
              className="mt-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg transition-colors"
            >
              Retry
            </button>
          </div>
        </div>
      </ProtectedLayout>
    );
  }

  return (
    <DashboardLayout>
      <div className="space-y-8">
        {/* Header */}
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          <div>
            <h2 className="text-3xl font-bold tracking-tight text-white">Users</h2>
            <p className="mt-1 text-zinc-400">
              Manage team members and their permissions.
            </p>
          </div>
          <div className="flex gap-2 w-full sm:w-auto">
            <Button
              variant="outline"
              onClick={handleRefresh}
              disabled={refreshing}
              className="flex-1 sm:flex-none glass border-white/10 text-white hover:bg-white/10"
            >
              <RefreshCw className={`h-4 w-4 mr-2 ${refreshing ? 'animate-spin' : ''}`} />
              {refreshing ? 'Refreshing...' : 'Refresh'}
            </Button>
            <Button className="flex-1 sm:flex-none bg-indigo-600 hover:bg-indigo-500 text-white">
              <Plus className="h-4 w-4 mr-2" />
              Invite User
            </Button>
          </div>
        </div>

        {/* Stats Grid */}
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          <Card className="border-white/10 bg-white/5 backdrop-blur-sm">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium text-zinc-400">
                Total Users
              </CardTitle>
              <UsersIcon className="h-4 w-4 text-blue-400" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-white">{stats.total}</div>
              <p className="text-xs text-zinc-500 mt-1">
                {stats.active} active members
              </p>
            </CardContent>
          </Card>

          <Card className="border-white/10 bg-white/5 backdrop-blur-sm">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium text-zinc-400">
                Active Users
              </CardTitle>
              <UserCheck className="h-4 w-4 text-emerald-400" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-white">{stats.active}</div>
              <p className="text-xs text-zinc-500 mt-1">
                {Math.round((stats.active / stats.total) * 100)}% of total
              </p>
            </CardContent>
          </Card>

          <Card className="border-white/10 bg-white/5 backdrop-blur-sm">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium text-zinc-400">
                Verified Email
              </CardTitle>
              <MailIcon className="h-4 w-4 text-amber-400" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-white">{stats.verified}</div>
              <p className="text-xs text-zinc-500 mt-1">
                {Math.round((stats.verified / stats.total) * 100)}% verified
              </p>
            </CardContent>
          </Card>

          <Card className="border-white/10 bg-white/5 backdrop-blur-sm">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium text-zinc-400">
                Admins
              </CardTitle>
              <Shield className="h-4 w-4 text-purple-400" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-white">{stats.admins}</div>
              <p className="text-xs text-zinc-500 mt-1">
                {stats.managers} managers total
              </p>
            </CardContent>
          </Card>
        </div>

        {/* Search and Filter */}
        <div className="flex flex-col lg:flex-row gap-4">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-zinc-400" />
            <Input
              placeholder="Search users..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-10 bg-white/5 border-white/10 text-white placeholder:text-zinc-400"
            />
          </div>
          <div className="flex flex-col sm:flex-row gap-2">
            <CustomSelect
              value={roleFilter}
              onChange={(value) => setRoleFilter(value as UserRole | "all")}
              options={[
                { value: "all", label: "All Roles" },
                { value: UserRole.ADMIN, label: "Admin" },
                { value: UserRole.MANAGER, label: "Manager" },
                { value: UserRole.MEMBER, label: "Member" },
                { value: UserRole.VIEWER, label: "Viewer" },
              ]}
              className="w-full sm:w-[140px]"
            />
            <CustomSelect
              value={statusFilter}
              onChange={(value) => setStatusFilter(value as "all" | "active" | "inactive")}
              options={[
                { value: "all", label: "All Status" },
                { value: "active", label: "Active" },
                { value: "inactive", label: "Inactive" },
              ]}
              className="w-full sm:w-[140px]"
            />
            <Button variant="outline" className="glass border-white/10 text-white hover:bg-white/5">
              <Filter className="h-4 w-4 mr-2" />
              More
            </Button>
          </div>
        </div>

        {/* Users List */}
        <Card className="border-white/10 bg-white/5 backdrop-blur-sm">
          <CardContent className="p-0">
            <div className="divide-y divide-white/10">
              {filteredUsers.map((user) => (
                <div key={user.id} className="p-6 hover:bg-white/5 transition-colors">
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                    <div className="flex items-center gap-4">
                      {/* Avatar */}
                      <div className="h-12 w-12 rounded-full bg-zinc-700 border border-white/10 flex items-center justify-center shrink-0 overflow-hidden relative group">
                        {user.avatar ? (
                          <img
                            src={getAvatarUrl(user.avatar)}
                            alt={`${user.firstName} ${user.lastName}`}
                            className="h-full w-full object-cover transition-transform duration-300 group-hover:scale-110"
                            onError={(e) => {
                              const target = e.target as HTMLImageElement;
                              target.style.display = 'none';
                              // Determine initials from parent scope or fallback
                              const parent = target.parentElement;
                              if (parent) {
                                // We can't easily re-render React here, but we can show the fallback by hiding the image
                                // The fallback initials span is separate, so maybe we structure this differently:
                                // Image ON TOP of initials? Or switch ref?
                                // Simpler approach: toggle a state? No, list is mapped.
                                // Best approach: Use CSS to hide image if broken, and have initials underneath?
                                // OR: Just let the initials be behind it.
                              }
                            }}
                          />
                        ) : null}
                        <span className={`text-lg font-medium text-zinc-300 absolute ${user.avatar ? '-z-10' : ''}`}>
                          {(user.firstName && typeof user.firstName === 'string' ? user.firstName[0] : '')}
                          {(user.lastName && typeof user.lastName === 'string' ? user.lastName[0] : '')}
                        </span>
                      </div>

                      {/* User Info */}
                      <div className="min-w-0 flex-1">
                        <div className="flex flex-wrap items-center gap-3 mb-1">
                          <h3 className="text-lg font-semibold text-white truncate">
                            {user.firstName} {user.lastName}
                          </h3>
                          {getStatusBadge(user)}
                          {getRoleBadge(user.role)}
                        </div>

                        <div className="flex flex-wrap items-center gap-4 text-sm text-zinc-400">
                          <div className="flex items-center gap-1">
                            <Mail className="h-3 w-3" />
                            <span className="truncate">{user.email}</span>
                          </div>
                          <div className="flex items-center gap-1">
                            <User className="h-3 w-3" />
                            <span>@{user.username}</span>
                          </div>
                          <div className="flex items-center gap-1">
                            <Activity className="h-3 w-3" />
                            <span>{formatLastLogin(user.lastLoginAt)}</span>
                          </div>
                        </div>
                      </div>
                    </div>

                    {/* Actions */}
                    <div className="flex items-center gap-2 self-end sm:self-auto">
                      <Button variant="ghost" size="sm" className="text-zinc-400 hover:text-white">
                        <Edit className="h-4 w-4 mr-1" />
                        Edit
                      </Button>
                      {user.isActive ? (
                        <Button variant="ghost" size="sm" className="text-zinc-400 hover:text-red-400">
                          <UserX className="h-4 w-4 mr-1" />
                          Deactivate
                        </Button>
                      ) : (
                        <Button variant="ghost" size="sm" className="text-zinc-400 hover:text-emerald-400">
                          <UserCheck className="h-4 w-4 mr-1" />
                          Activate
                        </Button>
                      )}
                      <Button variant="ghost" size="sm" className="text-zinc-400 hover:text-white">
                        <MoreVertical className="h-4 w-4" />
                      </Button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* Empty State */}
        {filteredUsers.length === 0 && (
          <div className="text-center py-12">
            <div className="mx-auto h-12 w-12 rounded-full bg-white/5 flex items-center justify-center mb-4">
              <Search className="h-6 w-6 text-zinc-400" />
            </div>
            <h3 className="text-lg font-medium text-white mb-2">No users found</h3>
            <p className="text-zinc-400 mb-6">
              {searchQuery || roleFilter !== "all" || statusFilter !== "all"
                ? "Try adjusting your search or filter criteria."
                : "No users have been added to your team yet."}
            </p>
            {!searchQuery && roleFilter === "all" && statusFilter === "all" && (
              <Button className="bg-indigo-600 hover:bg-indigo-500 text-white">
                <Plus className="h-4 w-4 mr-2" />
                Invite First User
              </Button>
            )}
          </div>
        )}

        {/* Role Distribution */}
        {users.length > 0 && (
          <Card className="border-white/10 bg-white/5 backdrop-blur-sm">
            <CardHeader>
              <CardTitle className="text-lg font-semibold text-white">Role Distribution</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
                <div className="flex items-center justify-between p-4 rounded-lg bg-white/5">
                  <div className="flex items-center gap-3">
                    <Crown className="h-5 w-5 text-purple-400" />
                    <span className="text-zinc-300">Admins</span>
                  </div>
                  <span className="text-white font-semibold">{stats.admins}</span>
                </div>
                <div className="flex items-center justify-between p-4 rounded-lg bg-white/5">
                  <div className="flex items-center gap-3">
                    <Shield className="h-5 w-5 text-blue-400" />
                    <span className="text-zinc-300">Managers</span>
                  </div>
                  <span className="text-white font-semibold">{stats.managers}</span>
                </div>
                <div className="flex items-center justify-between p-4 rounded-lg bg-white/5">
                  <div className="flex items-center gap-3">
                    <User className="h-5 w-5 text-emerald-400" />
                    <span className="text-zinc-300">Members</span>
                  </div>
                  <span className="text-white font-semibold">{stats.members}</span>
                </div>
                <div className="flex items-center justify-between p-4 rounded-lg bg-white/5">
                  <div className="flex items-center gap-3">
                    <User className="h-5 w-5 text-zinc-400" />
                    <span className="text-zinc-300">Viewers</span>
                  </div>
                  <span className="text-white font-semibold">{stats.viewers}</span>
                </div>
              </div>
            </CardContent>
          </Card>
        )}
      </div>
    </DashboardLayout>
  );
}