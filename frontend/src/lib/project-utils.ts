import type { Project, User } from "@/types";
import { ProjectStatus } from "@/types";
import { getAvatarUrl } from "@/lib/utils";

// Colors for projects
export const PROJECT_COLORS = ["#6366f1", "#10b981", "#f59e0b", "#ef4444", "#8b5cf6"];

/**
 * Transforms backend project data into a fully typed Project object.
 * Handles missing fields with robust defaults.
 */
export function transformProjectData(project: any, currentUser?: User, index: number = 0): Project {
    // Find owner from member summaries with fallback
    const ownerMember = project.memberSummaries?.find((m: any) => m.role === 'owner');

    // Safely extract owner name
    const getOwnerName = (): string => {
        if (ownerMember?.name) { return ownerMember.name; }
        if (project.ownerName) { return project.ownerName; }
        if (currentUser?.id === project.ownerId && currentUser?.name) { return currentUser.name; }
        return "Unknown User";
    };

    const ownerName = getOwnerName();
    const ownerId = project.ownerId ?? currentUser?.id ?? "unknown";

    // Construct Owner User object
    const owner: User = {
        id: ownerId,
        email: ownerMember?.email ?? currentUser?.email ?? "unknown@company.com",
        username: ownerMember?.name?.toLowerCase().replace(/\s+/g, '') ??
            currentUser?.username ??
            ownerName.toLowerCase().replace(/\s+/g, '') ??
            "unknownuser",
        firstName: ownerMember?.name?.split(' ')[0] ??
            ownerName.split(' ')[0] ??
            currentUser?.firstName ??
            "Unknown",
        lastName: ownerMember?.name?.split(' ').slice(1).join(' ') ??
            ownerName.split(' ').slice(1).join(' ') ??
            currentUser?.lastName ??
            "User",
        role: "admin" as any, // Owner is always admin-like
        isActive: true, // simplified
        emailVerified: true,
        createdAt: project.createdAt ?? new Date().toISOString(),
        updatedAt: project.updatedAt ?? new Date().toISOString(),
        avatar: getAvatarUrl(ownerMember?.avatar ?? currentUser?.avatar)
    };

    // Map Members
    const members = (project.memberSummaries ?? project.members ?? []).map((m: any, index: number) => ({
        id: m.id ?? `member-${m.userId}-${index}`,
        userId: m.userId ?? m.id ?? "unknown",
        projectId: project.id,
        role: m.role ?? "member",
        joinedAt: m.joinedAt ?? new Date().toISOString(),
        user: {
            id: m.userId ?? m.id ?? "unknown",
            email: m.email ?? "unknown@company.com",
            name: m.name ?? ownerName,
            avatar: getAvatarUrl(m.avatar),
            role: m.role ?? "member",
            isActive: m.isActive !== false,
            emailVerified: m.emailVerified !== false,
            createdAt: m.createdAt ?? new Date().toISOString(),
            updatedAt: m.updatedAt ?? new Date().toISOString()
        }
    }));

    // Map Stats
    const stats = {
        totalTasks: Number(project.taskCount ?? project.task_count ?? project.totalTasks ?? 0),
        completedTasks: Number(project.completedTasks ?? project.completed_tasks ?? 0),
        inProgressTasks: (Number(project.taskCount ?? project.task_count ?? 0)) - (Number(project.completedTasks ?? project.completed_tasks ?? 0)),
        overdueTasks: Number(project.overdueTasks ?? project.overdue_tasks ?? 0),
        teamMembers: Number(project.memberCount ?? project.member_count ?? members.length ?? 1),
        recentActivity: Number(project.recentActivity ?? project.recent_activity ?? 0)
    };

    // Map Settings
    const settings = {
        allowPublicAccess: project.settings?.allowPublicAccess ?? false,
        requireApproval: project.settings?.requireApproval !== false,
        defaultTaskVisibility: project.settings?.defaultTaskVisibility ?? "team",
        notificationSettings: {
            taskAssigned: project.settings?.notificationSettings?.taskAssigned !== false,
            statusChanged: project.settings?.notificationSettings?.statusChanged !== false,
            deadlineApproaching: project.settings?.notificationSettings?.deadlineApproaching !== false,
            commentAdded: project.settings?.notificationSettings?.commentAdded !== false
        }
    };

    return {
        id: project.id,
        name: project.name ?? "Unnamed Project",
        description: project.description ?? "",
        color: project.color ?? PROJECT_COLORS[index % PROJECT_COLORS.length], // fallback color
        status: project.isActive !== false ? ProjectStatus.ACTIVE : ProjectStatus.ARCHIVED,
        ownerId,
        owner,
        members,
        stats,
        settings,
        createdAt: project.createdAt ?? new Date().toISOString(),
        updatedAt: project.updatedAt ?? new Date().toISOString(),
        // extra properties for backward compatibility if needed, but keeping Project interface clean is better
        taskCount: stats.totalTasks,
        completedTasks: stats.completedTasks,
        memberCount: stats.teamMembers
    } as Project;
}
