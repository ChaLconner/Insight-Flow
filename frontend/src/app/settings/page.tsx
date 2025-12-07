"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { ProtectedLayout } from "@/components/layout/ProtectedLayout";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import {
  User,
  Bell,
  Shield,
  Palette,
  Key,
  Database,
  Save,
  Camera,
  Eye,
  EyeOff,
  Mail,
  Moon,
  Sun,
  Monitor
} from "lucide-react";
import { Skeleton } from "@/components/ui/skeleton";
import { useAuthStore } from "@/stores/auth-store";
import { usersApi, authApi, fileApi } from "@/lib/api-endpoints";
import type { UserProfile } from "@/types";
import { CustomSelect } from "@/components/ui/custom-select";
import { API_CONFIG } from "@/lib/constants";
import { getAvatarUrl } from "@/lib/utils";
import { Switch } from "@/components/ui/switch";
import { toast } from "sonner";
import { getErrorMessage } from "@/lib/error-utils";

export default function SettingsPage() {
  const [activeTab, setActiveTab] = useState("profile");
  const [showPassword, setShowPassword] = useState(false);
  const [theme, setTheme] = useState("dark");
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [uploading, setUploading] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Define types for local state
  interface NotificationState {
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

  // Use auth store actions
  const {
    isAuthenticated,
    isLoading,
    user,
    fetchUserProfile
  } = useAuthStore();

  // Use a local loading for the initial data fetch if needed
  const [isInitializing, setIsInitializing] = useState(true);

  // Password state
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [passwordStrength, setPasswordStrength] = useState(0);

  const calculateStrength = (password: string) => {
    let strength = 0;
    if (password.length > 6) strength += 25;
    if (password.match(/[A-Z]/)) strength += 25;
    if (password.match(/[0-9]/)) strength += 25;
    if (password.match(/[^A-Za-z0-9]/)) strength += 25;
    return strength;
  };

  useEffect(() => {
    setPasswordStrength(calculateStrength(newPassword));
  }, [newPassword]);

  // Initialize data
  useEffect(() => {
    if (!isAuthenticated && !isLoading) {
      // Not authenticated, just stop loading
      setIsInitializing(false);
      return;
    }

    if (isAuthenticated && user) {
      // We have user data, we can populate the form
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
        avatar: rawProfile.avatar ?? rawProfile.avatar_url ?? rawProfile.avatarUrl ?? ""
      });

      // Load settings
      loadSettings();

      setIsInitializing(false);
    } else if (isAuthenticated && !user) {
      // We need to fetch the user
      fetchUserProfile().then(() => {
        // The useEffect will re-run when user is updated
      }).catch(() => {
        setIsInitializing(false);
      });
    }
  }, [isAuthenticated, user, isLoading]);

  const loadSettings = async () => {
    try {
      const userSettings = await usersApi.getSettings().catch(() => null);
      if (userSettings) {
        setTheme(userSettings.theme ?? "dark");
        if (userSettings.notificationPreferences) {
          // Safely merge saved preferences with defaults
          setNotifications(prev => ({
            email: {
              ...prev.email,
              ...(userSettings.notificationPreferences.email || {})
            },
            inApp: {
              ...prev.inApp,
              ...(userSettings.notificationPreferences.inApp || {})
            }
          }));
        }
      }
    } catch (e) {
      console.warn('Failed to load user settings', e);
    }
  };

  const handleUpdatePassword = async () => {
    if (newPassword !== confirmPassword) {
      console.error("Password validation failed: passwords do not match");
      setError("Passwords do not match");
      return;
    }
    if (passwordStrength < 50) {
      console.error("Password validation failed: password too weak");
      setError("Password is too weak");
      return;
    }

    try {
      setSaving(true);
      const response = await authApi.changePassword(currentPassword, newPassword);
      toast.success("Password updated successfully");
      setCurrentPassword("");
      setNewPassword("");
      setConfirmPassword("");
      setError(null);
    } catch (err: any) {
      console.error("Password change error:", err);
      const errorMessage = getErrorMessage(err);
      setError(errorMessage);
      toast.error("Failed to update password", {
        description: errorMessage
      });
    } finally {
      setSaving(false);
    }
  };

  // Mock user profile data
  const [profileData, setProfileData] = useState({
    firstName: "",
    lastName: "",
    email: "",
    username: "",
    phone: "",
    bio: "",
    avatar: ""
  });


  // Notification settings
  const [notifications, setNotifications] = useState<NotificationState>({
    email: {
      tasks: true,
      projects: true,
      mentions: true
    },
    inApp: {
      tasks: true,
      projects: true,
      mentions: true,
      updates: true,
      system: true
    }
  });


  const handleRefresh = () => {
    setRefreshing(true);
    Promise.all([
      fetchUserProfile(),
      loadSettings()
    ]).then(() => {
      toast.success("Refreshed successfully");
    }).finally(() => {
      setRefreshing(false);
    });
  };

  const handleSaveSettings = async () => {
    if (!user) {
      return;
    }

    try {
      setSaving(true);
      setError(null);

      // 1. Prepare profile update
      const updateData = {
        ...profileData,
        first_name: profileData.firstName,
        last_name: profileData.lastName,
        name: `${profileData.firstName} ${profileData.lastName}`.trim()
      };

      // 2. Prepare settings update
      const settingsData = {
        theme,
        notificationPreferences: notifications
      };

      // Use store action for user profile update
      const { updateUserProfile } = useAuthStore.getState();

      await Promise.all([
        updateUserProfile(updateData),
        usersApi.updateSettings(settingsData)
      ]);

      toast.success('Settings saved successfully!');
    } catch (err) {
      console.error('Error saving settings:', err);
      const errorMessage = getErrorMessage(err);
      setError(errorMessage);
      toast.error("Failed to save settings", {
        description: errorMessage
      });
    } finally {
      setSaving(false);
    }
  };

  const tabs = [
    { id: "profile", label: "Profile", icon: User },
    { id: "notifications", label: "Notifications", icon: Bell },
    { id: "security", label: "Security", icon: Shield },
    { id: "appearance", label: "Appearance", icon: Palette },
    { id: "billing", label: "Billing", icon: Database },
  ];

  const handleAvatarClick = () => {
    fileInputRef.current?.click();
  };

  const handleFileChange = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) {
      return;
    }

    // Validation
    const validTypes = ['image/jpeg', 'image/png', 'image/gif', 'image/webp'];
    if (!validTypes.includes(file.type)) {
      setError("Invalid file type. Please upload PNG, JPG, or GIF.");
      return;
    }

    if (file.size > 2 * 1024 * 1024) { // 2MB
      setError("File size too large. Maximum size is 2MB.");
      return;
    }

    // Create optimistic preview
    const previewUrl = URL.createObjectURL(file);
    const previousAvatar = profileData.avatar;

    try {
      setUploading(true);
      setError(null);

      // Show preview immediately
      setProfileData(prev => ({ ...prev, avatar: previewUrl }));

      const formData = new FormData();
      formData.append('file', file);

      const updatedUser = await usersApi.uploadAvatar(formData);

      if (updatedUser) {
        // Update with real URL from server
        const { updateUserAvatar } = useAuthStore.getState();
        const avatarUrl = updatedUser.avatar || "";
        updateUserAvatar(avatarUrl); // Update global store
        setProfileData(prev => ({ ...prev, avatar: avatarUrl }));
      }
    } catch (err) {
      console.error('Failed to upload avatar:', err);
      const errorMessage = getErrorMessage(err);
      setError(errorMessage);
      toast.error("Failed to upload avatar", { description: errorMessage });
      // Revert to previous avatar on error
      setProfileData(prev => ({ ...prev, avatar: previousAvatar }));
    } finally {
      setUploading(false);
      // Construct a new FileList or reset the input
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    }
  };

  const renderProfileTab = () => (
    <div className="space-y-6">
      <Card className="glass-card">
        <CardHeader>
          <CardTitle className="text-lg font-semibold text-white flex items-center gap-2">
            <User className="h-5 w-5" />
            Personal Information
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="flex flex-col sm:flex-row items-center gap-6">
            <div
              className="relative group cursor-pointer"
              onClick={handleAvatarClick}
            >
              <div className="h-24 w-24 rounded-full overflow-hidden ring-2 ring-white/10 group-hover:ring-indigo-500/50 transition-all duration-300 bg-zinc-800 flex items-center justify-center">
                {profileData.avatar ? (
                  <img
                    src={getAvatarUrl(profileData.avatar)}
                    alt="Profile"
                    className="h-full w-full object-cover group-hover:scale-110 transition-transform duration-500"
                    onError={(e) => {
                      e.currentTarget.style.display = 'none';
                      e.currentTarget.parentElement?.classList.add('fallback-active');
                    }}
                  />
                ) : (
                  <User className="h-10 w-10 text-zinc-400" />
                )}
              </div>
              <div className="absolute inset-0 bg-black/40 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity duration-300 rounded-full">
                <Camera className="h-8 w-8 text-white" />
              </div>
              <input
                type="file"
                ref={fileInputRef}
                className="hidden"
                accept="image/*"
                onChange={handleFileChange}
              />
            </div>
            <div className="space-y-2 text-center sm:text-left">
              <h3 className="text-lg font-medium text-white">Profile Picture</h3>
              <p className="text-sm text-zinc-400">
                PNG, JPG or GIF no bigger than 2MB
              </p>
              <Button
                variant="ghost"
                size="sm"
                className="border border-white/10 text-white bg-transparent hover:bg-white/10 transition-all hover:scale-105 active:scale-95"
                onClick={handleAvatarClick}
                disabled={uploading}
              >
                {uploading ? 'Uploading...' : 'Change Avatar'}
              </Button>
            </div>
          </div>

          <div className="grid gap-4 md:grid-cols-2">
            <div className="space-y-2">
              <Label htmlFor="firstName" className="text-zinc-300">First Name</Label>
              <Input
                id="firstName"
                value={profileData.firstName}
                onChange={(e) => setProfileData({ ...profileData, firstName: e.target.value })}
                className="form-input !text-zinc-100 bg-zinc-900/50 border-white/10 focus:bg-zinc-900/80 focus:border-indigo-500/50 font-medium placeholder:text-zinc-500"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="lastName" className="text-zinc-300">Last Name</Label>
              <Input
                id="lastName"
                value={profileData.lastName}
                onChange={(e) => setProfileData({ ...profileData, lastName: e.target.value })}
                className="form-input !text-zinc-100 bg-zinc-900/50 border-white/10 focus:bg-zinc-900/80 focus:border-indigo-500/50 font-medium placeholder:text-zinc-500"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="email" className="text-zinc-300">Email</Label>
              <Input
                id="email"
                type="email"
                value={profileData.email}
                onChange={(e) => setProfileData({ ...profileData, email: e.target.value })}
                className="form-input !text-zinc-100 bg-zinc-900/50 border-white/10 focus:bg-zinc-900/80 focus:border-indigo-500/50 font-medium placeholder:text-zinc-500"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="username" className="text-zinc-300">Username</Label>
              <Input
                id="username"
                value={profileData.username}
                onChange={(e) => setProfileData({ ...profileData, username: e.target.value })}
                className="form-input !text-zinc-100 bg-zinc-900/50 border-white/10 focus:bg-zinc-900/80 focus:border-indigo-500/50 font-medium placeholder:text-zinc-500"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="phone" className="text-zinc-300">Phone</Label>
              <Input
                id="phone"
                type="tel"
                value={profileData.phone}
                onChange={(e) => setProfileData({ ...profileData, phone: e.target.value })}
                className="form-input !text-zinc-100 bg-zinc-900/50 border-white/10 focus:bg-zinc-900/80 focus:border-indigo-500/50 font-medium placeholder:text-zinc-500"
              />
            </div>
          </div>

          <div className="space-y-2">
            <Label htmlFor="bio" className="text-zinc-300">Bio</Label>
            <textarea
              id="bio"
              value={profileData.bio}
              onChange={(e) => setProfileData({ ...profileData, bio: e.target.value })}
              className="flex min-h-[100px] w-full rounded-md border border-white/10 bg-zinc-900/50 px-3 py-2 text-sm !text-zinc-100 placeholder:text-zinc-500 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500 disabled:cursor-not-allowed disabled:opacity-50"
              placeholder="Tell us a little about yourself"
            />
          </div>
        </CardContent>
      </Card>
    </div>
  );

  const renderNotificationsTab = () => (
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

  const renderSecurityTab = () => (
    <div className="space-y-6">
      <Card className="glass-card">
        <CardHeader>
          <CardTitle className="text-lg font-semibold text-white flex items-center gap-2">
            <Key className="h-5 w-5" />
            Change Password
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <Label className="text-zinc-300">Current Password</Label>
            <div className="relative">
              <Input
                type={showPassword ? "text" : "password"}
                value={currentPassword}
                autoComplete="new-password"
                onChange={(e) => setCurrentPassword(e.target.value)}
                className="form-input !text-zinc-100 bg-zinc-900/50 border-white/10 focus:bg-zinc-900/80 focus:border-indigo-500/50 font-medium pr-10 placeholder:text-zinc-500"
              />
              <Button
                type="button"
                variant="ghost"
                size="sm"
                className="absolute right-0 top-0 h-full px-3 py-2 hover:bg-transparent text-zinc-400 hover:text-white"
                onClick={() => setShowPassword(!showPassword)}
              >
                {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
              </Button>
            </div>
          </div>
          <div className="space-y-2">
            <Label className="text-zinc-300">New Password</Label>
            <div className="relative">
              <Input
                type={showPassword ? "text" : "password"}
                value={newPassword}
                autoComplete="new-password"
                onChange={(e) => setNewPassword(e.target.value)}
                className="form-input !text-zinc-100 bg-zinc-900/50 border-white/10 focus:bg-zinc-900/80 focus:border-indigo-500/50 font-medium pr-10 placeholder:text-zinc-500"
              />
              <Button
                type="button"
                variant="ghost"
                size="sm"
                className="absolute right-0 top-0 h-full px-3 py-2 hover:bg-transparent text-zinc-400 hover:text-white"
                onClick={() => setShowPassword(!showPassword)}
              >
                {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
              </Button>
            </div>
            {/* Password Strength Indicator */}
            {newPassword && (
              <div className="space-y-1">
                <div className="flex justify-between text-xs text-zinc-400">
                  <span>Strength</span>
                  <span>{passwordStrength < 30 ? 'Weak' : passwordStrength < 70 ? 'Medium' : 'Strong'}</span>
                </div>
                <div className="h-1.5 w-full bg-zinc-700 rounded-full overflow-hidden">
                  <div
                    className={`h-full transition-all duration-300 ${passwordStrength < 30 ? 'bg-red-500' :
                      passwordStrength < 70 ? 'bg-yellow-500' : 'bg-green-500'
                      }`}
                    style={{ width: `${passwordStrength}%` }}
                  />
                </div>
              </div>
            )}
          </div>
          <div className="space-y-2">
            <Label className="text-zinc-300">Confirm Password</Label>
            <div className="relative">
              <Input
                type={showPassword ? "text" : "password"}
                value={confirmPassword}
                autoComplete="new-password"
                onChange={(e) => setConfirmPassword(e.target.value)}
                className="form-input !text-zinc-100 bg-zinc-900/50 border-white/10 focus:bg-zinc-900/80 focus:border-indigo-500/50 font-medium pr-10 placeholder:text-zinc-500"
              />
              <Button
                type="button"
                variant="ghost"
                size="sm"
                className="absolute right-0 top-0 h-full px-3 py-2 hover:bg-transparent text-zinc-400 hover:text-white"
                onClick={() => setShowPassword(!showPassword)}
              >
                {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
              </Button>
            </div>
          </div>
          <Button
            onClick={handleUpdatePassword}
            disabled={saving || !currentPassword || !newPassword || !confirmPassword}
            className="w-full sm:w-auto"
          >
            Update Password
          </Button>
        </CardContent>
      </Card>

      <Card className="glass-card">
        <CardHeader>
          <CardTitle className="text-lg font-semibold text-white flex items-center gap-2">
            <Shield className="h-5 w-5" />
            Two-Factor Authentication
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-between">
            <div>
              <p className="text-white font-medium">Secure your account</p>
              <p className="text-zinc-400 text-sm">Add an extra layer of security to your account.</p>
            </div>
            <Button variant="ghost" className="border border-white/10 text-white bg-transparent hover:bg-white/10" onClick={() => toast.info("2FA setup is coming soon!")}>
              Setup 2FA
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );

  const renderAppearanceTab = () => (
    <div className="space-y-6">
      <Card className="glass-card">
        <CardHeader>
          <CardTitle className="text-lg font-semibold text-white flex items-center gap-2">
            <Palette className="h-5 w-5" />
            Theme
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="grid grid-cols-3 gap-4">
            {[
              { id: 'light', label: 'Light', icon: Sun, color: 'bg-zinc-100' },
              { id: 'dark', label: 'Dark', icon: Moon, color: 'bg-zinc-900' },
              { id: 'system', label: 'Auto', icon: Monitor, color: 'bg-gradient-to-br from-zinc-100 to-zinc-900' },
            ].map((option) => (
              <div
                key={option.id}
                onClick={() => setTheme(option.id)}
                className={`group relative p-4 rounded-xl border-2 cursor-pointer transition-all duration-300 ${theme === option.id
                  ? 'border-indigo-500 bg-indigo-500/10 shadow-lg shadow-indigo-500/10'
                  : 'border-white/10 hover:border-white/20 hover:bg-white/5'
                  }`}
              >
                <div className={`h-16 w-full rounded-lg mb-3 ${option.color} opacity-80 group-hover:opacity-100 transition-opacity`} />
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <option.icon className={`h-4 w-4 ${theme === option.id ? 'text-indigo-400' : 'text-zinc-400 group-hover:text-white'}`} />
                    <span className={`font-medium ${theme === option.id ? 'text-white' : 'text-zinc-400 group-hover:text-white'}`}>
                      {option.label}
                    </span>
                  </div>
                  {theme === option.id && (
                    <div className="h-2 w-2 rounded-full bg-indigo-500 shadow-[0_0_8px_rgba(99,102,241,0.5)]" />
                  )}
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );


  const renderBillingTab = () => (
    <div className="space-y-6">
      {/* Current Plan */}
      <Card className="glass-card">
        <CardHeader>
          <CardTitle className="text-lg font-semibold text-white">Current Plan</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center justify-between p-4 rounded-lg bg-white/5">
            <div>
              <h3 className="text-lg font-semibold text-white">Pro Plan</h3>
              <p className="text-zinc-400">$29/month • Billed monthly</p>
              <p className="text-sm text-zinc-500 mt-1">Next billing: February 18, 2024</p>
            </div>
            <Badge className="bg-emerald-500/20 text-emerald-400">Active</Badge>
          </div>

          <div className="flex gap-3">
            <Button variant="glass">
              Change Plan
            </Button>
            <Button variant="glass">
              Cancel Subscription
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Usage */}
      <Card className="glass-card">
        <CardHeader>
          <CardTitle className="text-lg font-semibold text-white">Usage This Month</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-3">
            <div className="flex justify-between">
              <span className="text-zinc-400">Projects</span>
              <span className="text-white">3 / 10</span>
            </div>
            <div className="h-2 rounded-full bg-white/10">
              <div className="h-full rounded-full bg-indigo-500 w-[30%]" />
            </div>
          </div>

          <div className="space-y-3">
            <div className="flex justify-between">
              <span className="text-zinc-400">Storage</span>
              <span className="text-white">2.4 GB / 10 GB</span>
            </div>
            <div className="h-2 rounded-full bg-white/10">
              <div className="h-full rounded-full bg-blue-500 w-[24%]" />
            </div>
          </div>

          <div className="space-y-3">
            <div className="flex justify-between">
              <span className="text-zinc-400">Team Members</span>
              <span className="text-white">6 / 25</span>
            </div>
            <div className="h-2 rounded-full bg-white/10">
              <div className="h-full rounded-full bg-emerald-500 w-[24%]" />
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Payment Method */}
      <Card className="glass-card">
        <CardHeader>
          <CardTitle className="text-lg font-semibold text-white">Payment Method</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center justify-between p-4 rounded-lg bg-white/5">
            <div className="flex items-center gap-3">
              <div className="h-8 w-12 bg-gradient-to-r from-blue-500 to-purple-500 rounded flex items-center justify-center">
                <span className="text-white text-xs font-bold">VISA</span>
              </div>
              <div>
                <p className="text-white font-medium">•••• •••• •••• 4242</p>
                <p className="text-zinc-400 text-sm">Expires 12/26</p>
              </div>
            </div>
            <Button variant="ghost" size="sm" className="border border-white/10 text-white bg-transparent hover:bg-white/10">
              Update
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );

  const renderTabContent = () => {
    switch (activeTab) {
      case "profile": return renderProfileTab();
      case "notifications": return renderNotificationsTab();
      case "security": return renderSecurityTab();
      case "appearance": return renderAppearanceTab();
      case "billing": return renderBillingTab();
      default: return renderProfileTab();
    }
  };

  return (
    <ProtectedLayout>
      <div className="space-y-8">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          <div>
            <h1 className="text-3xl font-bold text-white tracking-tight">Settings</h1>
            <p className="text-zinc-400 mt-1">Manage your account settings and preferences</p>
          </div>
          <div className="flex gap-3">
            <Button
              className="bg-indigo-600 hover:bg-indigo-500 text-white shadow-lg shadow-indigo-500/20"
              onClick={handleSaveSettings}
              disabled={saving}
            >
              <Save className="h-4 w-4 mr-2" />
              {saving ? 'Saving...' : 'Save Changes'}
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
                      className={`flex-shrink-0 lg:flex-shrink lg:w-full flex items-center gap-3 px-4 py-3 rounded-lg text-sm font-medium transition-all duration-200 whitespace-nowrap ${activeTab === tab.id
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
              {renderTabContent()}
            </div>
          </div>
        </div>
      </div>
    </ProtectedLayout>
  );
}