"use client";

import React, { memo } from "react";
import Image from "next/image";
import { Mail, User, Activity } from "lucide-react";
import { RoleBadge, StatusBadge } from "./UserBadges";
import { getAvatarUrl } from "@/lib/utils";

import type { User as UserType } from "@/types";

interface UserCardProps {
  user: UserType;
  formatLastLogin: (dateString?: string) => string;
}

function UserCardComponent({ user, formatLastLogin }: UserCardProps) {
  const fullName =
    `${user.firstName ?? ""} ${user.lastName ?? ""}`.trim() || "Unknown User";
  const initials =
    `${user.firstName?.[0] ?? ""}${user.lastName?.[0] ?? ""}`.toUpperCase();

  return (
    <div className="p-6 hover:bg-accent/50 transition-colors">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="flex items-center gap-4">
          {/* Avatar */}
          <div
            className="h-12 w-12 rounded-full bg-secondary border border-border flex items-center justify-center shrink-0 overflow-hidden relative group"
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
              className={`text-lg font-medium text-muted-foreground absolute ${user.avatar ? "-z-10" : ""}`}
              aria-hidden="true"
            >
              {initials}
            </span>
          </div>

          {/* User Info */}
          <div className="min-w-0 flex-1">
            <div className="flex flex-wrap items-center gap-3 mb-1">
              <h3 className="text-lg font-semibold text-foreground truncate">
                {fullName}
              </h3>
              <StatusBadge user={user} />
              <RoleBadge role={user.role} />
            </div>

            <div className="flex flex-wrap items-center gap-4 text-sm text-muted-foreground">
              <div className="flex items-center gap-1">
                <Mail className="h-3 w-3 shrink-0" aria-hidden="true" />
                <span
                  className="truncate max-w-[150px] sm:max-w-[220px]"
                  title={user.email}
                >
                  {user.email}
                </span>
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
      </div>
    </div>
  );
}

// Memoize to prevent unnecessary re-renders
export const UserCard = memo(UserCardComponent);
