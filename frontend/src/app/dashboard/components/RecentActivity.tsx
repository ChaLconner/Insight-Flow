"use client";

import React, { memo } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ActivityItem, ActivityItemData } from "./ActivityItem";

interface RecentActivityProps {
    activities: ActivityItemData[];
}

const RecentActivity = memo(function RecentActivity({ activities }: RecentActivityProps) {
    return (
        <Card className="col-span-3 border-white/10 bg-white/5 backdrop-blur-sm">
            <CardHeader>
                <CardTitle className="text-lg font-semibold text-white">Recent Activity</CardTitle>
            </CardHeader>
            <CardContent>
                <div className="space-y-8">
                    {activities.length > 0 ? (
                        activities.map((activity, index) => (
                            <ActivityItem
                                key={activity.id || index}
                                activity={activity}
                                isLast={index === activities.length - 1}
                            />
                        ))
                    ) : (
                        <EmptyActivityState />
                    )}
                </div>
            </CardContent>
        </Card>
    );
});

// Separate empty state component - memoized
const EmptyActivityState = memo(function EmptyActivityState() {
    return (
        <div className="text-center text-zinc-400 py-8">
            No recent activity
        </div>
    );
});

RecentActivity.displayName = 'RecentActivity';
EmptyActivityState.displayName = 'EmptyActivityState';

export { RecentActivity };
