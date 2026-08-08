import type { Project, User, UserRole } from "@/types";
import { ProjectStatus } from "@/types";
import { PROJECT_COLORS } from "@/lib/constants";
import { getAvatarUrl } from "@/lib/utils";

const DEFAULT_PROJECT_COLOR = "#6366f1";

/**
 * Keep legacy projects visually distinct when backend still returns its
 * default color. Explicit project colors remain unchanged.
 */
export function getProjectColor(color: unknown, index = 0): string {
  const normalizedColor = typeof color === "string" ? color.trim() : "";

  if (normalizedColor && normalizedColor.toLowerCase() !== DEFAULT_PROJECT_COLOR) {
    return normalizedColor;
  }

  return PROJECT_COLORS[index % PROJECT_COLORS.length];
}

/**
 * Transforms backend project data into a fully typed Project object.
 * Handles missing fields with robust defaults.
 */
export function transformProjectData(
  project: unknown,
  currentUser?: User,
  index: number = 0,
): Project {
  const p = project as Record<string, unknown>;
  // Find owner from member summaries with fallback
  const ownerMember = (p.memberSummaries as Record<string, unknown>[])?.find(
    (m) => m.role === "owner",
  );

  // Safely extract owner name
  const getOwnerName = (): string => {
    if (ownerMember?.name) {
      return ownerMember.name as string;
    }
    if (p.ownerName) {
      return p.ownerName as string;
    }
    if (currentUser?.id === p.ownerId && currentUser?.name) {
      return currentUser.name;
    }
    return "Unknown User";
  };

  const ownerName = getOwnerName();
  const ownerId = (p.ownerId as string) ?? currentUser?.id ?? "unknown";

  // Construct Owner User object
  const owner: User = {
    id: ownerId,
    email: (ownerMember?.email as string) ?? currentUser?.email ?? "unknown@company.com",
    username:
      ownerName.toLowerCase().replace(/\s+/g, "") ??
      "unknownuser",
    firstName:
      (ownerMember?.name as string)?.split(" ")[0] ??
      ownerName.split(" ")[0] ??
      currentUser?.firstName ??
      "Unknown",
    lastName:
      (ownerMember?.name as string)?.split(" ").slice(1).join(" ") ??
      ownerName.split(" ").slice(1).join(" ") ??
      currentUser?.lastName ??
      "User",
    role: "admin" as UserRole, // Owner is always admin-like
    isActive: true, // simplified
    emailVerified: true,
    createdAt: (p.createdAt as string) ?? new Date().toISOString(),
    updatedAt: (p.updatedAt as string) ?? new Date().toISOString(),
    avatar: getAvatarUrl(ownerMember?.avatar as string ?? currentUser?.avatar),
  };

  // Map Members
  const members = ((p.memberSummaries as Record<string, unknown>[]) ?? (p.members as Record<string, unknown>[]) ?? []).map(
    (m, index) => ({
      id: (m.id as string) ?? `member-${m.userId}-${index}`,
      userId: (m.userId as string) ?? (m.id as string) ?? "unknown",
      projectId: p.id as string,
      role: (m.role as string) ?? "member",
      joinedAt: (m.joinedAt as string) ?? new Date().toISOString(),
      user: {
        id: (m.userId as string) ?? (m.id as string) ?? "unknown",
        email: (m.email as string) ?? "unknown@company.com",
        name: (m.name as string) ?? (m.username as string) ?? "Unknown",
        avatar: getAvatarUrl(m.avatar as string),
        role: (m.role as UserRole) ?? "member",
        isActive: m.isActive !== false,
        emailVerified: m.emailVerified !== false,
        createdAt: (m.createdAt as string) ?? new Date().toISOString(),
        updatedAt: (m.updatedAt as string) ?? new Date().toISOString(),
      },
    }),
  );

  // Map Stats
  const stats = {
    totalTasks: Number(
      p.taskCount ?? p.task_count ?? p.totalTasks ?? 0,
    ),
    completedTasks: Number(
      p.completedTasks ?? p.completed_tasks ?? 0,
    ),
    inProgressTasks:
      Number(p.taskCount ?? p.task_count ?? 0) -
      Number(p.completedTasks ?? p.completed_tasks ?? 0),
    overdueTasks: Number(p.overdueTasks ?? p.overdue_tasks ?? 0),
    teamMembers: Number(
      p.memberCount ?? p.member_count ?? members.length ?? 1,
    ),
    recentActivity: Number(
      p.recentActivity ?? p.recent_activity ?? 0,
    ),
  };

  // Map Settings
  const pSettings = p.settings as Record<string, unknown> | undefined;
  const settings = {
    allowPublicAccess: pSettings?.allowPublicAccess ?? false,
    requireApproval: pSettings?.requireApproval !== false,
    defaultTaskVisibility: pSettings?.defaultTaskVisibility ?? "team",
    notificationSettings: {
      taskAssigned:
        ((pSettings?.notificationSettings as Record<string, unknown>)?.taskAssigned) !== false,
      statusChanged:
        ((pSettings?.notificationSettings as Record<string, unknown>)?.statusChanged) !== false,
      deadlineApproaching:
        ((pSettings?.notificationSettings as Record<string, unknown>)?.deadlineApproaching) !== false,
      commentAdded:
        ((pSettings?.notificationSettings as Record<string, unknown>)?.commentAdded) !== false,
    },
  };

  return {
    id: p.id as string,
    name: (p.name as string) ?? "Unnamed Project",
    description: (p.description as string) ?? "",
    color: getProjectColor(p.color, index),
    status:
      p.isActive !== false
        ? ProjectStatus.ACTIVE
        : ProjectStatus.ARCHIVED,
    ownerId,
    owner,
    members,
    stats,
    settings,
    createdAt: (p.createdAt as string) ?? new Date().toISOString(),
    updatedAt: (p.updatedAt as string) ?? new Date().toISOString(),
    // extra properties for backward compatibility if needed, but keeping Project interface clean is better
    taskCount: stats.totalTasks,
    completedTasks: stats.completedTasks,
    memberCount: stats.teamMembers,
  } as Project;
}
