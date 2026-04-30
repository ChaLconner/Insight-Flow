"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Bell, Mail, CheckCircle2 } from "lucide-react";
import { toast } from "sonner";
import { usersApi } from "@/lib/api-endpoints";

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

const DEFAULT_NOTIFICATION_PREFERENCES: NotificationState = {
  email: {
    tasks: true,
    projects: true,
    mentions: true,
  },
  inApp: {
    tasks: true,
    projects: true,
    mentions: true,
    updates: true,
    system: true,
  },
};

const AUTOSAVE_DELAY_MS = 600;

// ===================================
// Component
// ===================================

export function NotificationsSettings() {
  // Settings component with preferences state

  const [isLoading, setIsLoading] = useState(true);
  const [preferences, setPreferences] = useState<NotificationState>(DEFAULT_NOTIFICATION_PREFERENCES);
  const saveTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const pendingSaveRef = useRef<NotificationState | null>(null);
  const saveVersionRef = useRef(0);

  useEffect(() => {
    return () => {
      if (saveTimerRef.current) {
        clearTimeout(saveTimerRef.current);
      }
      if (pendingSaveRef.current) {
        void usersApi.updateSettings({
          notificationPreferences: pendingSaveRef.current,
        });
      }
    };
  }, []);

  // Load settings on mount
  useEffect(() => {
    const loadSettings = async () => {
      try {
        setIsLoading(true);
        const userSettings = await usersApi.getSettings().catch(() => null) as { notificationPreferences?: { email?: Partial<EmailNotificationSettings>; inApp?: Partial<InAppNotificationSettings> } } | null;
        if (userSettings?.notificationPreferences) {
          setPreferences((prev) => ({
            email: {
              ...prev.email,
              ...(userSettings.notificationPreferences?.email ?? {}),
            },
            inApp: {
              ...prev.inApp,
              ...(userSettings.notificationPreferences?.inApp ?? {}),
            },
          }));
        }
      } catch {
        // Silent failure - use defaults
      } finally {
        setIsLoading(false);
      }
    };

    loadSettings();
  }, []);

  const persistSettings = useCallback((newState: NotificationState) => {
    saveVersionRef.current += 1;
    const saveVersion = saveVersionRef.current;
    pendingSaveRef.current = newState;

    if (saveTimerRef.current) {
      clearTimeout(saveTimerRef.current);
    }

    saveTimerRef.current = setTimeout(() => {
      saveTimerRef.current = null;
      usersApi
        .updateSettings({
          notificationPreferences: newState,
        })
        .then(() => {
          if (saveVersion === saveVersionRef.current) {
            pendingSaveRef.current = null;
          }
        })
        .catch(() => {
          if (saveVersion === saveVersionRef.current) {
            toast.error("Failed to save notification preferences");
          }
        });
    }, AUTOSAVE_DELAY_MS);
  }, []);

  const handleToggleInApp = (key: keyof InAppNotificationSettings, checked: boolean) => {
    const newState = {
      ...preferences,
      inApp: { ...preferences.inApp, [key]: checked },
    };
    setPreferences(newState);
    persistSettings(newState);
  };

  const handleToggleEmail = (key: keyof EmailNotificationSettings, checked: boolean) => {
    const newState = {
      ...preferences,
      email: { ...preferences.email, [key]: checked },
    };
    setPreferences(newState);
    persistSettings(newState);
  };

  // Count enabled notifications
  const enabledInAppCount = Object.values(preferences.inApp).filter(Boolean).length;
  const enabledEmailCount = Object.values(preferences.email).filter(Boolean).length;

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div className="h-64 animate-pulse bg-muted rounded-xl" />
        <div className="h-48 animate-pulse bg-muted rounded-xl" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* In-App Notifications Section */}
      <Card className="border-border bg-card">
        <CardHeader className="pb-4">
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="text-lg font-semibold text-foreground flex items-center gap-2">
                <Bell className="h-5 w-5 text-emerald-500" />
                In-App Notifications
              </CardTitle>
              <p className="text-sm text-muted-foreground mt-1">
                Choose which notifications appear in the notification center
              </p>
            </div>
            <div className="hidden sm:flex items-center gap-2 text-xs text-muted-foreground">
              <CheckCircle2 className="h-3.5 w-3.5 text-emerald-500" />
              <span>{enabledInAppCount} of {Object.keys(preferences.inApp).length} enabled</span>
            </div>
          </div>
        </CardHeader>
        <CardContent className="space-y-1">
          {(Object.keys(preferences.inApp) as Array<keyof InAppNotificationSettings>).map((key) => {
            const config = inAppNotificationLabels[key];
            const isEnabled = preferences.inApp[key];

            return (
              <div
                key={key}
                className={`flex items-center justify-between py-3 px-4 rounded-lg transition-colors border ${
                  isEnabled
                    ? "bg-primary/20 border-primary/30 shadow-sm"
                    : "border-transparent hover:bg-white/5"
                }`}
              >
                <div className="flex-1 pr-4">
                  <Label className="text-foreground font-medium cursor-pointer flex items-center gap-2">
                    {config.label}
                    {isEnabled && (
                      <span className={`text-xs ${config.color ?? 'text-emerald-500'}`}>•</span>
                    )}
                  </Label>
                  <p className="text-xs text-muted-foreground mt-1">
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
      <Card className="border-border bg-card">
        <CardHeader className="pb-4">
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="text-lg font-semibold text-foreground flex items-center gap-2">
                <Mail className="h-5 w-5 text-blue-500" />
                Email Notifications
              </CardTitle>
              <p className="text-sm text-muted-foreground mt-1">
                Receive email updates for important activities
              </p>
            </div>
            <div className="hidden sm:flex items-center gap-2 text-xs text-muted-foreground">
              <CheckCircle2 className="h-3.5 w-3.5 text-blue-500" />
              <span>{enabledEmailCount} of {Object.keys(preferences.email).length} enabled</span>
            </div>
          </div>
        </CardHeader>
        <CardContent className="space-y-1">
          {(Object.keys(preferences.email) as Array<keyof EmailNotificationSettings>).map((key) => {
            const config = emailNotificationLabels[key];
            const isEnabled = preferences.email[key];

            return (
              <div
                key={key}
                className={`flex items-center justify-between py-3 px-4 rounded-lg transition-colors border ${
                  isEnabled
                    ? "bg-primary/20 border-primary/30 shadow-sm"
                    : "border-transparent hover:bg-white/5"
                }`}
              >
                <div className="flex-1 pr-4">
                  <Label className="text-foreground font-medium cursor-pointer">
                    {config.label}
                  </Label>
                  <p className="text-xs text-muted-foreground mt-1">
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
    </div>
  );
}
