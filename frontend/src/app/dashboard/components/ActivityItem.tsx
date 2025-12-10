"use client";

import React, { memo, useCallback } from "react";
import Image from "next/image";
import { formatDistanceToNow } from "date-fns";
import { getAvatarUrl } from "@/lib/utils";

// Static class names
const AVATAR_CONTAINER_CLASSES = "h-8 w-8 rounded-full bg-zinc-800 border border-white/10 flex items-center justify-center overflow-hidden shrink-0 group";
const TIMELINE_LINE_CLASSES = "absolute left-4 top-8 h-full w-px bg-white/10";

export interface ActivityItemData {
    id: string;
    user?: {
        name?: string;
        id?: string;
        avatar?: string;
    } | null;
    action: string;
    target?: string;
    time?: string;
    timestamp?: string;
    project?: string | { name: string; id?: string };
}

interface ActivityItemProps {
    activity: ActivityItemData;
    isLast: boolean;
}

const ActivityItem = memo(function ActivityItem({ activity, isLast }: ActivityItemProps) {
    const userName = activity.user?.name || 'Unknown User';
    const userAvatar = activity.user?.avatar;
    const activityTime = activity.time || activity.timestamp;

    // Get initials from name
    const userInitials = userName
        .split(' ')
        .map((n: string) => n[0])
        .join('')
        .toUpperCase();

    // Get project name - handle both string and object formats
    const projectName = typeof activity.project === 'string'
        ? activity.project
        : activity.project?.name;

    // Target to display
    const displayTarget = activity.target || projectName || '';

    // Format time
    const formattedTime = activityTime
        ? formatDistanceToNow(new Date(activityTime), { addSuffix: true })
        : '';

    // Handle image error
    const handleImageError = useCallback((e: React.SyntheticEvent<HTMLImageElement>) => {
        e.currentTarget.style.display = 'none';
        const fallback = e.currentTarget.nextElementSibling;
        if (fallback) {
            fallback.classList.remove('hidden');
        }
    }, []);

    return (
        <div className="flex gap-4">
            <div className="relative">
                <div className={AVATAR_CONTAINER_CLASSES}>
                    {userAvatar ? (
                        <div className="relative h-full w-full">
                            <Image
                                src={getAvatarUrl(userAvatar)}
                                alt={userName}
                                fill
                                className="object-cover"
                                sizes="32px"
                                onError={(e) => {
                                    const target = e.target as HTMLImageElement;
                                    target.style.display = 'none';
                                    const next = target.parentElement?.nextElementSibling;
                                    if (next) next.classList.remove('hidden');
                                }}
                            />
                        </div>
                    ) : null}
                    <span className={`${userAvatar ? 'hidden' : ''} text-xs font-medium text-zinc-400`}>
                        {userInitials}
                    </span>
                </div>
                {!isLast && (
                    <div className={TIMELINE_LINE_CLASSES} />
                )}
            </div>
            <div className="space-y-1">
                <p className="text-sm text-zinc-300">
                    <span className="font-medium text-white">{userName}</span>{" "}
                    {activity.action}{" "}
                    {displayTarget && (
                        <span className="text-indigo-400">{displayTarget}</span>
                    )}
                </p>
                {formattedTime && (
                    <p className="text-xs text-zinc-500">{formattedTime}</p>
                )}
            </div>
        </div>
    );
});

ActivityItem.displayName = 'ActivityItem';

export { ActivityItem };
