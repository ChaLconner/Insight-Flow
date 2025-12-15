"use client";

import { useState, useEffect } from "react";
import dynamic from "next/dynamic";
import { ProtectedLayout } from "@/components/layout/ProtectedLayout";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { User, Bell, Shield, Palette, Database, Save } from "lucide-react";
import { useAuthStore } from "@/stores/auth-store";
import { usersApi, authApi } from "@/lib/api-endpoints";
import { toast } from "sonner";
import { getErrorMessage } from "@/lib/error-utils";

// Direct import for LCP optimization (Profile is default tab)
import { ProfileSettings } from "./components/profile-settings";
import type { NotificationState } from "./components/notifications-settings";

// Dynamic imports for other tabs to reduce initial bundle size
const NotificationsSettings = dynamic(
  () =>
    import("./components/notifications-settings").then(
      (mod) => mod.NotificationsSettings,
    ),
  {
    loading: () => (
      <div className="h-96 animate-pulse bg-zinc-800/50 rounded-xl" />
    ),
  },
);
const SecuritySettings = dynamic(
  () =>
    import("./components/security-settings").then(
      (mod) => mod.SecuritySettings,
    ),
  {
    loading: () => (
      <div className="h-96 animate-pulse bg-zinc-800/50 rounded-xl" />
    ),
  },
);
const AppearanceSettings = dynamic(
  () =>
    import("./components/appearance-settings").then(
      (mod) => mod.AppearanceSettings,
    ),
  {
    loading: () => (
      <div className="h-96 animate-pulse bg-zinc-800/50 rounded-xl" />
    ),
  },
);
const BillingSettings = dynamic(
  () =>
    import("./components/billing-settings").then((mod) => mod.BillingSettings),
  {
    loading: () => (
      <div className="h-96 animate-pulse bg-zinc-800/50 rounded-xl" />
    ),
  },
);

export default function SettingsPage() {
  const [activeTab, setActiveTab] = useState("profile");

  // Profile State
  const [profileData, setProfileData] = useState({
    firstName: "",
    lastName: "",
    email: "",
    username: "",
    phone: "",
    bio: "",
    avatar: "",
  });
  const [uploading, setUploading] = useState(false);

  // Notification State
  const [notifications, setNotifications] = useState<NotificationState>({
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
  });

  // Security State
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [passwordStrength, setPasswordStrength] = useState(0);
  const [showPassword, setShowPassword] = useState(false);

  // Appearance State
  const [theme, setTheme] = useState("dark");

  // Common State
  const [isInitializing, setIsInitializing] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  const { isAuthenticated, isLoading, user, fetchUserProfile } = useAuthStore();

  const calculateStrength = (password: string) => {
    let strength = 0;
    // Backend requires at least 8 characters
    if (password.length >= 8) {
      strength += 25;
    }
    // Backend requires uppercase
    if (password.match(/[A-Z]/)) {
      strength += 25;
    }
    // Backend requires lowercase (implicit in typical valid passwords, but enforced by backend)
    if (password.match(/[a-z]/)) {
      strength += 15;
    }
    // Backend requires number from 0-9
    if (password.match(/[0-9]/)) {
      strength += 25;
    }
    // Special chars are good but not strictly required by this backend regex, keeping for good measure
    if (password.match(/[^A-Za-z0-9]/)) {
      strength += 10;
    }

    // Cap at 100
    return Math.min(strength, 100);
  };

  useEffect(() => {
    setPasswordStrength(calculateStrength(newPassword));
  }, [newPassword]);

  useEffect(() => {
    const init = async () => {
      if (!isAuthenticated && !isLoading) {
        setIsInitializing(false);
        return;
      }

      if (isAuthenticated) {
        if (user) {
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          const rawProfile = user as any;
          const firstName = rawProfile.firstName ?? rawProfile.first_name ?? "";
          const lastName = rawProfile.lastName ?? rawProfile.last_name ?? "";
          const name = rawProfile.name ?? "";

          let finalFirst = firstName;
          let finalLast = lastName;

          if (!finalFirst && name) {
            const parts = name.split(" ");
            finalFirst = parts[0];
            finalLast = parts.slice(1).join(" ");
          }

          setProfileData({
            firstName: finalFirst,
            lastName: finalLast,
            email: rawProfile.email ?? "",
            username: rawProfile.username ?? "",
            phone: rawProfile.phone ?? "",
            bio: rawProfile.bio ?? "",
            avatar:
              rawProfile.avatar ??
              rawProfile.avatar_url ??
              rawProfile.avatarUrl ??
              "",
          });

          await loadSettings();
        } else {
          try {
            await fetchUserProfile();
          } catch (e) {
            console.warn("Failed to fetch user profile", e);
          }
        }
        setIsInitializing(false);
      }
    };

    init();
  }, [isAuthenticated, user, isLoading, fetchUserProfile]);

  const loadSettings = async () => {
    try {
      const userSettings = await usersApi.getSettings().catch(() => null);
      if (userSettings) {
        setTheme(userSettings.theme ?? "dark");
        if (userSettings.notificationPreferences) {
          setNotifications((prev) => ({
            email: {
              ...prev.email,
              ...(userSettings.notificationPreferences.email ?? {}),
            },
            inApp: {
              ...prev.inApp,
              ...(userSettings.notificationPreferences.inApp ?? {}),
            },
          }));
        }
      }
    } catch (e) {
      console.warn("Failed to load user settings", e);
    }
  };

  const handleUpdatePassword = async () => {
    if (newPassword !== confirmPassword) {
      setError("Passwords do not match");
      return;
    }
    if (passwordStrength < 50) {
      setError("Password is too weak");
      return;
    }

    try {
      setSaving(true);
      await authApi.changePassword(currentPassword, newPassword);
      toast.success("Password updated successfully");
      setCurrentPassword("");
      setNewPassword("");
      setConfirmPassword("");
      setError(null);
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    } catch (err: any) {
      const errorMessage = getErrorMessage(err);
      setError(errorMessage);
      toast.error("Failed to update password", { description: errorMessage });
    } finally {
      setSaving(false);
    }
  };

  const handleSaveSettings = async () => {
    if (!user) {
      return;
    }

    try {
      setSaving(true);
      setError(null);

      const updateData = {
        ...profileData,
        first_name: profileData.firstName,
        last_name: profileData.lastName,
        name: `${profileData.firstName} ${profileData.lastName}`.trim(),
      };

      const settingsData = {
        theme,
        notificationPreferences: notifications,
      };

      const { updateUserProfile } = useAuthStore.getState();

      await Promise.all([
        updateUserProfile(updateData),
        usersApi.updateSettings(settingsData),
      ]);

      toast.success("Settings saved successfully!");
    } catch (err) {
      const errorMessage = getErrorMessage(err);
      setError(errorMessage);
      toast.error("Failed to save settings", { description: errorMessage });
    } finally {
      setSaving(false);
    }
  };

  const handleFileChange = async (
    event: React.ChangeEvent<HTMLInputElement>,
  ) => {
    const file = event.target.files?.[0];
    if (!file) {
      return;
    }

    const validTypes = ["image/jpeg", "image/png", "image/gif", "image/webp"];
    if (!validTypes.includes(file.type)) {
      setError("Invalid file type. Please upload PNG, JPG, or GIF.");
      return;
    }

    if (file.size > 2 * 1024 * 1024) {
      setError("File size too large. Maximum size is 2MB.");
      return;
    }

    const previewUrl = URL.createObjectURL(file);
    const previousAvatar = profileData.avatar;

    try {
      setUploading(true);
      setError(null);
      setProfileData((prev) => ({ ...prev, avatar: previewUrl }));

      const formData = new FormData();
      formData.append("file", file);

      const updatedUser = await usersApi.uploadAvatar(formData);

      if (updatedUser) {
        const { updateUserAvatar } = useAuthStore.getState();
        const avatarUrl = updatedUser.avatar ?? "";
        updateUserAvatar(avatarUrl);
        setProfileData((prev) => ({ ...prev, avatar: avatarUrl }));
      }
    } catch (err) {
      const errorMessage = getErrorMessage(err);
      setError(errorMessage);
      toast.error("Failed to upload avatar", { description: errorMessage });
      setProfileData((prev) => ({ ...prev, avatar: previousAvatar }));
    } finally {
      setUploading(false);
      // Reset input value if needed, but we don't have direct ref here.
      // The ProfileSettings component handles the ref.
      event.target.value = "";
    }
  };

  const tabs = [
    { id: "profile", label: "Profile", icon: User },
    { id: "notifications", label: "Notifications", icon: Bell },
    { id: "security", label: "Security", icon: Shield },
    { id: "appearance", label: "Appearance", icon: Palette },
    { id: "billing", label: "Billing", icon: Database },
  ];

  return (
    <ProtectedLayout>
      <div className="space-y-8">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          <div>
            <h1 className="text-3xl font-bold text-white tracking-tight">
              Settings
            </h1>
            <p className="text-zinc-400 mt-1">
              Manage your account settings and preferences
            </p>
          </div>
          <div className="flex gap-3">
            <Button
              className="bg-indigo-600 hover:bg-indigo-500 text-white shadow-lg shadow-indigo-500/20"
              onClick={handleSaveSettings}
              disabled={saving}
            >
              <Save className="h-4 w-4 mr-2" />
              {saving ? "Saving..." : "Save Changes"}
            </Button>
          </div>
        </div>

        {error && (
          <div className="bg-red-500/10 border border-red-500/20 text-red-400 px-4 py-3 rounded-lg">
            {error}
          </div>
        )}

        <div className="flex flex-col lg:grid lg:gap-8 lg:grid-cols-4">
          <div className="lg:col-span-1">
            <Card className="glass-card lg:sticky lg:top-8">
              <CardContent className="p-2">
                <nav className="flex flex-row lg:flex-col gap-2 lg:gap-0 lg:space-y-1 overflow-x-auto pb-2 lg:pb-0 scrollbar-hide">
                  {tabs.map((tab) => (
                    <button
                      key={tab.id}
                      onClick={() => setActiveTab(tab.id)}
                      className={`flex-shrink-0 lg:flex-shrink lg:w-full flex items-center gap-3 px-4 py-3 rounded-lg text-sm font-medium transition-all duration-200 whitespace-nowrap ${
                        activeTab === tab.id
                          ? "bg-indigo-600 text-white shadow-lg shadow-indigo-500/20"
                          : "text-zinc-400 hover:text-white hover:bg-white/5"
                      }`}
                    >
                      <tab.icon className="h-4 w-4" />
                      {tab.label}
                    </button>
                  ))}
                </nav>
              </CardContent>
            </Card>
          </div>

          <div className="lg:col-span-3">
            <div className="animate-in fade-in slide-in-from-bottom-4 duration-500">
              {activeTab === "profile" && (
                <ProfileSettings
                  profileData={profileData}
                  setProfileData={setProfileData}
                  uploading={uploading}
                  onFileChange={handleFileChange}
                  isLoading={isInitializing}
                />
              )}
              {activeTab === "notifications" && (
                <NotificationsSettings
                  notifications={notifications}
                  setNotifications={setNotifications}
                />
              )}
              {activeTab === "security" && (
                <SecuritySettings
                  currentPassword={currentPassword}
                  setCurrentPassword={setCurrentPassword}
                  newPassword={newPassword}
                  setNewPassword={setNewPassword}
                  confirmPassword={confirmPassword}
                  setConfirmPassword={setConfirmPassword}
                  passwordStrength={passwordStrength}
                  showPassword={showPassword}
                  setShowPassword={setShowPassword}
                  saving={saving}
                  onUpdatePassword={handleUpdatePassword}
                />
              )}
              {activeTab === "appearance" && (
                <AppearanceSettings theme={theme} setTheme={setTheme} />
              )}
              {activeTab === "billing" && <BillingSettings />}
            </div>
          </div>
        </div>
      </div>
    </ProtectedLayout>
  );
}
