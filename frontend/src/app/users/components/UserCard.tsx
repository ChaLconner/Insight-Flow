"use client";

import React, { memo, useCallback } from "react";
import Image from "next/image";
import { Button } from "@/components/ui/button";
import { Mail, User, Activity, Edit, UserX, UserCheck, MoreVertical } from "lucide-react";
import { RoleBadge, StatusBadge } from "./UserBadges";
import { getAvatarUrl } from "@/lib/utils";
import { toast } from "sonner";
import type { User as UserType } from "@/types";

interface UserCardProps {
    user: UserType;
    formatLastLogin: (dateString?: string) => string;
}

function UserCardComponent({ user, formatLastLogin }: UserCardProps) {
    const handleEdit = useCallback(() => {
        toast.info("Edit user feature coming soon");
    }, []);

    const handleToggleActive = useCallback(() => {
        if (user.isActive) {
            toast.info("Deactivate user feature coming soon");
        } else {
            toast.info("Activate user feature coming soon");
        }
    }, [user.isActive]);

    const fullName = `${user.firstName ?? ''} ${user.lastName ?? ''}`.trim() || 'Unknown User';
    const initials = `${user.firstName?.[0] ?? ''}${user.lastName?.[0] ?? ''}`.toUpperCase();

    return (
        <div className="p-6 hover:bg-white/5 transition-colors">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                <div className="flex items-center gap-4">
                    {/* Avatar */}
                    <div
                        className="h-12 w-12 rounded-full bg-zinc-700 border border-white/10 flex items-center justify-center shrink-0 overflow-hidden relative group"
                        role="img"
                        aria-label={`Avatar of ${fullName}`}
                    >
                        {user.avatar ? (
                            <Image
                                src={getAvatarUrl(user.avatar)}
                                alt={`${fullName}'s avatar`}
                                fill
                                className="object-cover transition-transform duration-300 group-hover:scale-110"
                                sizes="48px"
                            />
                        ) : null}
                        <span
                            className={`text-lg font-medium text-zinc-300 absolute ${user.avatar ? '-z-10' : ''}`}
                            aria-hidden="true"
                        >
                            {initials}
                        </span>
                    </div>

                    {/* User Info */}
                    <div className="min-w-0 flex-1">
                        <div className="flex flex-wrap items-center gap-3 mb-1">
                            <h3 className="text-lg font-semibold text-white truncate">
                                {fullName}
                            </h3>
                            <StatusBadge user={user} />
                            <RoleBadge role={user.role} />
                        </div>

                        <div className="flex flex-wrap items-center gap-4 text-sm text-zinc-400">
                            <div className="flex items-center gap-1">
                                <Mail className="h-3 w-3" aria-hidden="true" />
                                <span className="truncate">{user.email}</span>
                            </div>
                            {user.username && (
                                <div className="flex items-center gap-1">
                                    <User className="h-3 w-3" aria-hidden="true" />
                                    <span>@{user.username}</span>
                                </div>
                            )}
                            <div className="flex items-center gap-1">
                                <Activity className="h-3 w-3" aria-hidden="true" />
                                <span>{formatLastLogin(user.lastLoginAt)}</span>
                            </div>
                        </div>
                    </div>
                </div>

                {/* Actions */}
                <div className="flex items-center gap-2 self-end sm:self-auto" role="group" aria-label="User actions">
                    <Button
                        variant="ghost"
                        size="sm"
                        className="text-zinc-400 hover:text-white"
                        onClick={handleEdit}
                        aria-label={`Edit ${fullName}`}
                    >
                        <Edit className="h-4 w-4 mr-1" aria-hidden="true" />
                        Edit
                    </Button>
                    {user.isActive ? (
                        <Button
                            variant="ghost"
                            size="sm"
                            className="text-zinc-400 hover:text-red-400"
                            onClick={handleToggleActive}
                            aria-label={`Deactivate ${fullName}`}
                        >
                            <UserX className="h-4 w-4 mr-1" aria-hidden="true" />
                            Deactivate
                        </Button>
                    ) : (
                        <Button
                            variant="ghost"
                            size="sm"
                            className="text-zinc-400 hover:text-emerald-400"
                            onClick={handleToggleActive}
                            aria-label={`Activate ${fullName}`}
                        >
                            <UserCheck className="h-4 w-4 mr-1" aria-hidden="true" />
                            Activate
                        </Button>
                    )}
                    <Button
                        variant="ghost"
                        size="sm"
                        className="text-zinc-400 hover:text-white"
                        aria-label={`More options for ${fullName}`}
                    >
                        <MoreVertical className="h-4 w-4" aria-hidden="true" />
                    </Button>
                </div>
            </div>
        </div>
    );
}

// Memoize to prevent unnecessary re-renders
export const UserCard = memo(UserCardComponent);
