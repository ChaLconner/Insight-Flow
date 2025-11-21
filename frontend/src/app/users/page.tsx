"use client";

import { useState, useEffect } from "react";
// import { useUsers } from "@/hooks/use-api"; // Removed React Query
import { DashboardLayout } from "@/components/layout/DashboardLayout";
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
  User
} from "lucide-react";
import type { User as UserType } from "@/types";
import { UserRole } from "@/types";

export default function UsersPage() {
  // const { data: usersResponse, isLoading, error } = useUsers(); // Removed React Query
  // const users = usersResponse?.data || [];
  const users: UserType[] = []; // Empty array for now
  const isLoading = false;
  const error = null;
  const [searchQuery, setSearchQuery] = useState("");
  const [roleFilter, setRoleFilter] = useState<UserRole | "all">("all");
  const [statusFilter, setStatusFilter] = useState<"all" | "active" | "inactive">("all");

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
    return (
      <Badge className={config.color}>
        {config.icon}
        {config.label}
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

  return (
    <DashboardLayout>
      <div className="space-y-8">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-3xl font-bold tracking-tight text-white">Users</h2>
            <p className="mt-1 text-zinc-400">
              Manage team members and their permissions.
            </p>
          </div>
          <Button className="bg-indigo-600 hover:bg-indigo-500 text-white">
            <Plus className="h-4 w-4 mr-2" />
            Invite User
          </Button>
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
          <div className="flex gap-2">
            <select
              value={roleFilter}
              onChange={(e) => setRoleFilter(e.target.value as UserRole | "all")}
              className="rounded-lg bg-white/5 border border-white/10 px-3 py-2 text-white text-sm"
            >
              <option value="all">All Roles</option>
              <option value={UserRole.ADMIN}>Admin</option>
              <option value={UserRole.MANAGER}>Manager</option>
              <option value={UserRole.MEMBER}>Member</option>
              <option value={UserRole.VIEWER}>Viewer</option>
            </select>
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value as "all" | "active" | "inactive")}
              className="rounded-lg bg-white/5 border border-white/10 px-3 py-2 text-white text-sm"
            >
              <option value="all">All Status</option>
              <option value="active">Active</option>
              <option value="inactive">Inactive</option>
            </select>
            <Button variant="outline" size="sm" className="border-white/10 text-white hover:bg-white/5">
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
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-4">
                      {/* Avatar */}
                      <div className="h-12 w-12 rounded-full bg-zinc-700 border border-white/10 flex items-center justify-center">
                        <span className="text-lg font-medium text-zinc-300">
                          {(user.firstName && typeof user.firstName === 'string' ? user.firstName[0] : '')}
                          {(user.lastName && typeof user.lastName === 'string' ? user.lastName[0] : '')}
                        </span>
                      </div>

                      {/* User Info */}
                      <div className="min-w-0 flex-1">
                        <div className="flex items-center gap-3 mb-1">
                          <h3 className="text-lg font-semibold text-white truncate">
                            {user.firstName} {user.lastName}
                          </h3>
                          {getStatusBadge(user)}
                          {getRoleBadge(user.role)}
                        </div>
                        
                        <div className="flex items-center gap-4 text-sm text-zinc-400">
                          <div className="flex items-center gap-1">
                            <Mail className="h-3 w-3" />
                            <span>{user.email}</span>
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
                    <div className="flex items-center gap-2">
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