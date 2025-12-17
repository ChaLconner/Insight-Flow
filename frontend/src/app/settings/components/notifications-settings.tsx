"use client";

import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Button } from "@/components/ui/button";
import { Bell, Mail, FlaskConical, Loader2, CheckCircle2 } from "lucide-react";
import { toast } from "sonner";

// ===================================
// Type Definitions
// ===================================

export interface EmailNotificationSettings {
  tasks: boolean;
  projects: boolean;
  mentions: boolean;
}

export interface InAppNotificationSettings {
  tasks: boolean;
  projects: boolean;
  mentions: boolean;
  updates: boolean;
  system: boolean;
}

export interface NotificationState {
  email: EmailNotificationSettings;
  inApp: InAppNotificationSettings;
}

interface NotificationsSettingsProps {
  notifications: NotificationState;
  setNotifications: React.Dispatch<React.SetStateAction<NotificationState>>;
}

// ===================================
// Notification Labels Configuration
// ===================================

interface NotificationLabel {
  label: string;
  description: string;
  color?: string;
}

const inAppNotificationLabels: Record<keyof InAppNotificationSettings, NotificationLabel> = {
  tasks: {
    label: "Task Notifications",
    description: "Task assigned to you, status changes, and deadline reminders",
    color: "text-blue-400",
  },
  projects: {
    label: "Project Notifications",
    description: "When you're added to or removed from projects",
    color: "text-purple-400",
  },
  mentions: {
    label: "Mentions",
    description: "When someone mentions you in a comment",
    color: "text-amber-400",
  },
  updates: {
    label: "Updates",
    description: "Status changes on tasks you created or are watching",
    color: "text-emerald-400",
  },
  system: {
    label: "System Notifications",
    description: "Important system alerts and announcements",
    color: "text-rose-400",
  },
};

const emailNotificationLabels: Record<keyof EmailNotificationSettings, NotificationLabel> = {
  tasks: {
    label: "Task Updates",
    description: "Email when tasks are assigned or completed",
  },
  projects: {
    label: "Project Updates",
    description: "Email when added to new projects",
  },
  mentions: {
    label: "Mentions",
    description: "Email when someone mentions you",
  },
};

// ===================================
// Component
// ===================================

export function NotificationsSettings({
  notifications,
  setNotifications,
}: NotificationsSettingsProps) {
  const [isCreatingTest, setIsCreatingTest] = useState(false);

  const handleCreateTestNotifications = async () => {
    setIsCreatingTest(true);
    try {
      // Use API client for consistency - fallback to fetch if not available
      const response = await fetch('/api/notifications/create-test', {
        method: 'POST',
        credentials: 'include',
      });

      if (response.ok) {
        const data = await response.json();
        toast.success(data.message, {
          description: "Check the bell icon to see your notifications",
        });
      } else {
        toast.error("Failed to create test notifications");
      }
    } catch (error) {
      console.error("Error creating test notifications:", error);
      toast.error("Failed to create test notifications");
    } finally {
      setIsCreatingTest(false);
    }
  };

  const handleToggleInApp = (key: keyof InAppNotificationSettings, checked: boolean) => {
    setNotifications((prev) => ({
      ...prev,
      inApp: { ...prev.inApp, [key]: checked },
    }));
  };

  const handleToggleEmail = (key: keyof EmailNotificationSettings, checked: boolean) => {
    setNotifications((prev) => ({
      ...prev,
      email: { ...prev.email, [key]: checked },
    }));
  };

  // Count enabled notifications
  const enabledInAppCount = Object.values(notifications.inApp).filter(Boolean).length;
  const enabledEmailCount = Object.values(notifications.email).filter(Boolean).length;

  return (
    <div className="space-y-6">
      {/* In-App Notifications Section */}
      <Card className="glass-card border-emerald-500/20">
        <CardHeader className="pb-4">
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="text-lg font-semibold text-white flex items-center gap-2">
                <Bell className="h-5 w-5 text-emerald-400" />
                In-App Notifications
              </CardTitle>
              <p className="text-sm text-zinc-400 mt-1">
                Choose which notifications appear in the notification center
              </p>
            </div>
            <div className="hidden sm:flex items-center gap-2 text-xs text-zinc-500">
              <CheckCircle2 className="h-3.5 w-3.5 text-emerald-400" />
              <span>{enabledInAppCount} of {Object.keys(notifications.inApp).length} enabled</span>
            </div>
          </div>
        </CardHeader>
        <CardContent className="space-y-1">
          {(Object.keys(notifications.inApp) as Array<keyof InAppNotificationSettings>).map((key) => {
            const config = inAppNotificationLabels[key];
            const isEnabled = notifications.inApp[key];
            
            return (
              <div
                key={key}
                className={`flex items-center justify-between py-3 px-4 rounded-lg transition-colors border ${
                  isEnabled 
                    ? "bg-white/5 border-white/10 hover:border-emerald-500/30" 
                    : "border-transparent hover:bg-white/5"
                }`}
              >
                <div className="flex-1 pr-4">
                  <Label className="text-zinc-200 font-medium cursor-pointer flex items-center gap-2">
                    {config.label}
                    {isEnabled && (
                      <span className={`text-xs ${config.color ?? 'text-emerald-400'}`}>•</span>
                    )}
                  </Label>
                  <p className="text-xs text-zinc-500 mt-1">
                    {config.description}
                  </p>
                </div>
                <Switch
                  checked={isEnabled}
                  onCheckedChange={(checked) => handleToggleInApp(key, checked)}
                />
              </div>
            );
          })}
        </CardContent>
      </Card>

      {/* Email Notifications Section */}
      <Card className="glass-card border-blue-500/20">
        <CardHeader className="pb-4">
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="text-lg font-semibold text-white flex items-center gap-2">
                <Mail className="h-5 w-5 text-blue-400" />
                Email Notifications
              </CardTitle>
              <p className="text-sm text-zinc-400 mt-1">
                Receive email updates for important activities
              </p>
            </div>
            <div className="hidden sm:flex items-center gap-2 text-xs text-zinc-500">
              <CheckCircle2 className="h-3.5 w-3.5 text-blue-400" />
              <span>{enabledEmailCount} of {Object.keys(notifications.email).length} enabled</span>
            </div>
          </div>
        </CardHeader>
        <CardContent className="space-y-1">
          {(Object.keys(notifications.email) as Array<keyof EmailNotificationSettings>).map((key) => {
            const config = emailNotificationLabels[key];
            const isEnabled = notifications.email[key];
            
            return (
              <div
                key={key}
                className={`flex items-center justify-between py-3 px-4 rounded-lg transition-colors border ${
                  isEnabled 
                    ? "bg-white/5 border-white/10 hover:border-blue-500/30" 
                    : "border-transparent hover:bg-white/5"
                }`}
              >
                <div className="flex-1 pr-4">
                  <Label className="text-zinc-200 font-medium cursor-pointer">
                    {config.label}
                  </Label>
                  <p className="text-xs text-zinc-500 mt-1">
                    {config.description}
                  </p>
                </div>
                <Switch
                  checked={isEnabled}
                  onCheckedChange={(checked) => handleToggleEmail(key, checked)}
                />
              </div>
            );
          })}
        </CardContent>
      </Card>

      {/* Test Notifications */}
      <Card className="glass-card border-amber-500/20">
        <CardHeader className="pb-4">
          <CardTitle className="text-lg font-semibold text-white flex items-center gap-2">
            <FlaskConical className="h-5 w-5 text-amber-400" />
            Test Notifications
          </CardTitle>
          <p className="text-sm text-zinc-400 mt-1">
            Create sample notifications to test the system
          </p>
        </CardHeader>
        <CardContent>
          <Button
            onClick={handleCreateTestNotifications}
            disabled={isCreatingTest}
            className="bg-amber-600 hover:bg-amber-500 text-white"
          >
            {isCreatingTest ? (
              <>
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                Creating...
              </>
            ) : (
              <>
                <FlaskConical className="h-4 w-4 mr-2" />
                Create Test Notifications
              </>
            )}
          </Button>
          <p className="text-xs text-zinc-500 mt-3">
            This will create 5 sample notifications. Check the bell icon in the header to view them.
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
