"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Mail, Bell } from "lucide-react";

export interface NotificationState {
    email: {
        tasks: boolean;
        projects: boolean;
        mentions: boolean;
        [key: string]: boolean;
    };
    inApp: {
        tasks: boolean;
        projects: boolean;
        mentions: boolean;
        updates: boolean;
        system: boolean;
        [key: string]: boolean;
    };
}

interface NotificationsSettingsProps {
    notifications: NotificationState;
    setNotifications: React.Dispatch<React.SetStateAction<NotificationState>>;
}

export function NotificationsSettings({
    notifications,
    setNotifications
}: NotificationsSettingsProps) {
    return (
        <div className="space-y-6">
            <Card className="glass-card">
                <CardHeader>
                    <CardTitle className="text-lg font-semibold text-white flex items-center gap-2">
                        <Mail className="h-5 w-5" />
                        Email Notifications
                    </CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                    {Object.entries(notifications.email).map(([key, value]) => (
                        <div key={key} className="flex items-center justify-between">
                            <Label className="text-zinc-300 capitalize">{key}</Label>
                            <Switch
                                checked={value}
                                onCheckedChange={(checked) => setNotifications(prev => ({
                                    ...prev,
                                    email: { ...prev.email, [key]: checked }
                                }))}
                            />
                        </div>
                    ))}
                </CardContent>
            </Card>

            <Card className="glass-card">
                <CardHeader>
                    <CardTitle className="text-lg font-semibold text-white flex items-center gap-2">
                        <Bell className="h-5 w-5" />
                        In-App Notifications
                    </CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                    {Object.entries(notifications.inApp).map(([key, value]) => (
                        <div key={key} className="flex items-center justify-between">
                            <Label className="text-zinc-300 capitalize">{key}</Label>
                            <Switch
                                checked={value}
                                onCheckedChange={(checked) => setNotifications(prev => ({
                                    ...prev,
                                    inApp: { ...prev.inApp, [key]: checked }
                                }))}
                            />
                        </div>
                    ))}
                </CardContent>
            </Card>
        </div>
    );
}
