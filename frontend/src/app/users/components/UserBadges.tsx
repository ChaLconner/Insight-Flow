"use client";

import { Badge } from "@/components/ui/badge";
import { Crown, Shield, User, UserCheck, UserX, MailIcon } from "lucide-react";
import type { User as UserType } from "@/types";
import { UserRole } from "@/types";

// Role configuration - memoized at module level
const ROLE_CONFIG = {
  [UserRole.ADMIN]: {
    label: "Admin",
    color: "bg-purple-100 text-purple-700 dark:bg-purple-500/20 dark:text-purple-400",
    icon: Crown,
  },
  [UserRole.MANAGER]: {
    label: "Manager",
    color: "bg-blue-100 text-blue-700 dark:bg-blue-500/20 dark:text-blue-400",
    icon: Shield,
  },
  [UserRole.MEMBER]: {
    label: "Member",
    color: "bg-emerald-100 text-emerald-700 dark:bg-emerald-500/20 dark:text-emerald-400",
    icon: User,
  },
  [UserRole.VIEWER]: {
    label: "Viewer",
    color: "bg-muted text-muted-foreground",
    icon: User,
  },
} as const;

interface RoleBadgeProps {
  role: UserRole;
}

export function RoleBadge({ role }: RoleBadgeProps) {
  const config = ROLE_CONFIG[role];

  if (!config) {
    return (
      <Badge className="bg-muted text-muted-foreground">
        <User className="h-3 w-3 mr-1" />
        {role || "Unknown"}
      </Badge>
    );
  }

  const IconComponent = config.icon;

  return (
    <Badge className={config.color}>
      <IconComponent className="h-3 w-3 mr-1" />
      {config.label}
    </Badge>
  );
}

interface StatusBadgeProps {
  user: UserType;
}

export function StatusBadge({ user }: StatusBadgeProps) {
  if (!user.isActive) {
    return (
      <Badge className="bg-red-100 text-red-700 dark:bg-red-500/20 dark:text-red-400">
        <UserX className="h-3 w-3 mr-1" />
        Inactive
      </Badge>
    );
  }

  if (!user.emailVerified) {
    return (
      <Badge className="bg-amber-100 text-amber-700 dark:bg-amber-500/20 dark:text-amber-400">
        <MailIcon className="h-3 w-3 mr-1" />
        Unverified
      </Badge>
    );
  }

  return (
    <Badge className="bg-emerald-100 text-emerald-700 dark:bg-emerald-500/20 dark:text-emerald-400">
      <UserCheck className="h-3 w-3 mr-1" />
      Active
    </Badge>
  );
}
