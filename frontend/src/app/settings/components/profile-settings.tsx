"use client";

import { useRef, useState, useEffect } from "react";
import Image from "next/image";
import { Card, CardContent, CardHeader, CardTitle, CardFooter } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { User, Camera, Mail, Phone, AtSign, FileText, Save, Loader2 } from "lucide-react";
import { getAvatarUrl } from "@/lib/utils";
import { Skeleton } from "@/components/ui/skeleton";
import { useAuthStore } from "@/stores/auth-store";
import { usersApi } from "@/lib/api-endpoints";
import { toast } from "sonner";
import { getErrorMessage } from "@/lib/error-utils";
import { canSubmitProfileForm } from "./profile-settings.utils";

// Define proper types for profile data
export interface ProfileData {
  firstName: string;
  lastName: string;
  email: string;
  username: string;
  phone: string;
  bio: string;
  avatar: string;
}

interface ProfileSettingsProps {
  // We can keep these as optional if we want to allow override,
  // but we'll primarily use internal state now.
  isLoading?: boolean;
}

// Email validation regex
const EMAIL_REGEX = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

// Phone validation regex (international format)
const PHONE_REGEX = /^[+]?[(]?[0-9]{1,4}[)]?[-\s./0-9]*$/;

// Bio max length
const BIO_MAX_LENGTH = 100;

export function ProfileSettings({
  isLoading: initialLoading = false,
}: ProfileSettingsProps) {
  const user = useAuthStore((state) => state.user);
  const updateUserProfile = useAuthStore((state) => state.updateUserProfile);
  const updateUserAvatar = useAuthStore((state) => state.updateUserAvatar);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [profileData, setProfileData] = useState<ProfileData>({
    firstName: "",
    lastName: "",
    email: "",
    username: "",
    phone: "",
    bio: "",
    avatar: "",
  });

  const [isSaving, setIsSaving] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [isLoading, setIsLoading] = useState(initialLoading);

  // Initialize data from auth store
  useEffect(() => {
    if (user) {
      // Type-safe extraction of user profile fields
      const rawProfile = user as unknown as Record<string, string | undefined>;
      const firstName = rawProfile.firstName ?? rawProfile.first_name ?? "";
      const lastName = rawProfile.lastName ?? rawProfile.last_name ?? "";
      const name = rawProfile.name ?? "";

      let finalFirst = firstName;
      let finalLast = lastName;

      if (!finalFirst && name) {
        const parts = name.split(" ");
        finalFirst = parts[0] ?? "";
        finalLast = parts.slice(1).join(" ");
      }

      setProfileData({
        firstName: finalFirst,
        lastName: finalLast,
        email: rawProfile.email ?? "",
        username: rawProfile.username ?? rawProfile.name ?? "",
        phone: rawProfile.phone ?? "",
        bio: rawProfile.bio ?? "",
        avatar: rawProfile.avatar ?? rawProfile.avatar_url ?? rawProfile.avatarUrl ?? "",
      });
      setIsLoading(false);
    }
  }, [user]);

  const handleAvatarClick = () => {
    fileInputRef.current?.click();
  };

  const handleFileChange = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) {
      return;
    }

    const validTypes = ["image/jpeg", "image/png", "image/gif", "image/webp"];
    if (!validTypes.includes(file.type)) {
      toast.error("Invalid file type. Please upload PNG, JPG, or GIF.");
      return;
    }

    if (file.size > 2 * 1024 * 1024) {
      toast.error("File size too large. Maximum size is 2MB.");
      return;
    }

    const previewUrl = URL.createObjectURL(file);
    const previousAvatar = profileData.avatar;

    try {
      setIsUploading(true);
      // Optimistic UI
      setProfileData((prev) => ({ ...prev, avatar: previewUrl }));
      updateUserAvatar(previewUrl);

      const formData = new FormData();
      formData.append("file", file);

      const updatedUser = await usersApi.uploadAvatar(formData);

      if (updatedUser) {
        const avatarUrl = updatedUser.avatar ?? "";
        updateUserAvatar(avatarUrl);
        setProfileData((prev) => ({ ...prev, avatar: avatarUrl }));
        URL.revokeObjectURL(previewUrl);
        toast.success("Avatar updated successfully!");
      }
    } catch (err) {
      const errorMessage = getErrorMessage(err);
      toast.error("Failed to upload avatar", { description: errorMessage });
      setProfileData((prev) => ({ ...prev, avatar: previousAvatar }));
      updateUserAvatar(previousAvatar);
      URL.revokeObjectURL(previewUrl);
    } finally {
      setIsUploading(false);
      event.target.value = "";
    }
  };

  const handleSave = async () => {
    if (!user) {
      return;
    }

    // Validate
    if (!isEmailValid) {
      toast.error("Please enter a valid email address");
      return;
    }
    if (isBioOverLimit) {
      toast.error("Bio is too long");
      return;
    }
    if (!isPhoneValid) {
      toast.error("Please enter a valid phone number");
      return;
    }

    try {
      setIsSaving(true);
      const updateData = {
        ...profileData,
        first_name: profileData.firstName,
        last_name: profileData.lastName,
        name: `${profileData.firstName} ${profileData.lastName}`.trim(),
      };

      await updateUserProfile(updateData);
      toast.success("Profile saved successfully!");
    } catch (err) {
      const errorMessage = getErrorMessage(err);
      toast.error("Failed to save profile", { description: errorMessage });
    } finally {
      setIsSaving(false);
    }
  };

  // Validation helpers
  const isEmailValid = profileData.email === "" || EMAIL_REGEX.test(profileData.email);
  const isPhoneValid = profileData.phone === "" || PHONE_REGEX.test(profileData.phone);
  const bioLength = profileData.bio.length;
  const isBioOverLimit = bioLength > BIO_MAX_LENGTH;

  const isFormDirty = user && (
    profileData.firstName !== (user.firstName ?? (user as unknown as Record<string, string | undefined>).first_name ?? "") ||
    profileData.lastName !== (user.lastName ?? (user as unknown as Record<string, string | undefined>).last_name ?? "") ||
    profileData.email !== (user.email ?? "") ||
    profileData.username !== (user.username ?? "") ||
    profileData.phone !== ((user as unknown as Record<string, string | undefined>).phone ?? "") ||
    profileData.bio !== ((user as unknown as Record<string, string | undefined>).bio ?? "")
  );
  const canSaveProfile = canSubmitProfileForm({
    hasUser: Boolean(user),
    isSaving,
    isFormDirty: Boolean(isFormDirty),
    isEmailValid,
    isPhoneValid,
    isBioOverLimit,
  });

  return (
    <div className="space-y-6">
      <Card className="border-border bg-card">
        <CardHeader>
          <CardTitle className="text-lg font-semibold text-foreground flex items-center gap-2">
            <User className="h-5 w-5" />
            Personal Information
          </CardTitle>
          <p className="text-sm text-muted-foreground mt-1">
            Update your personal details and public profile
          </p>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* Avatar Section */}
          <div className="flex flex-col sm:flex-row items-center gap-6 p-4 rounded-xl bg-accent/20 border border-border">
            <div
              className="relative group cursor-pointer"
              onClick={isLoading ? undefined : handleAvatarClick}
            >
              <div className="relative h-24 w-24 rounded-full overflow-hidden ring-2 ring-border group-hover:ring-primary/50 transition-all duration-300 bg-secondary flex items-center justify-center">
                {isLoading ? (
                  <Skeleton className="h-full w-full" />
                ) : profileData.avatar ? (
                  <Image
                    src={getAvatarUrl(profileData.avatar)}
                    alt="Profile"
                    fill
                    priority
                    className="object-cover group-hover:scale-110 transition-transform duration-500"
                    sizes="96px"
                  />
                ) : (
                  <User className="h-10 w-10 text-muted-foreground" />
                )}
              </div>
              {!isLoading && (
                <div className="absolute inset-0 bg-black/40 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity duration-300 rounded-full">
                  <Camera className="h-8 w-8 text-white" />
                </div>
              )}
              <input
                type="file"
                ref={fileInputRef}
                className="hidden"
                accept="image/*"
                onChange={handleFileChange}
                disabled={isLoading}
              />
            </div>
            <div className="space-y-2 text-center sm:text-left">
              <h3 className="text-lg font-medium text-foreground">
                Profile Picture
              </h3>
              <p className="text-sm text-muted-foreground">
                PNG, JPG or GIF no bigger than 2MB
              </p>
              {isLoading ? (
                <Skeleton className="h-9 w-32" />
              ) : (
                <Button
                  variant="ghost"
                  size="sm"
                  className="border border-border text-foreground hover:bg-accent hover:text-accent-foreground transition-all hover:scale-105 active:scale-95"
                  onClick={handleAvatarClick}
                  disabled={isUploading}
                >
                  {isUploading ? (
                    <>
                      <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                      Uploading...
                    </>
                  ) : "Change Avatar"}
                </Button>
              )}
            </div>
          </div>

          {/* Form Fields */}
          <div className="grid gap-5 md:grid-cols-2">
            {/* First Name */}
            <div className="space-y-2">
              <Label htmlFor="firstName" className="text-muted-foreground flex items-center gap-2">
                <User className="h-3.5 w-3.5 text-muted-foreground" />
                First Name
              </Label>
              {isLoading ? (
                <Skeleton className="h-10 w-full" />
              ) : (
                <Input
                  id="firstName"
                  name="firstName"
                  autoComplete="given-name"
                  value={profileData.firstName}
                  onChange={(e) =>
                    setProfileData((prev) => ({
                      ...prev,
                      firstName: e.target.value,
                    }))
                  }
                  placeholder="Enter your first name"
                  className="bg-background border-input text-foreground focus:border-primary focus:ring-primary placeholder:text-muted-foreground"
                />
              )}
            </div>

            {/* Last Name */}
            <div className="space-y-2">
              <Label htmlFor="lastName" className="text-muted-foreground flex items-center gap-2">
                <User className="h-3.5 w-3.5 text-muted-foreground" />
                Last Name
              </Label>
              {isLoading ? (
                <Skeleton className="h-10 w-full" />
              ) : (
                <Input
                  id="lastName"
                  name="lastName"
                  autoComplete="family-name"
                  value={profileData.lastName}
                  onChange={(e) =>
                    setProfileData((prev) => ({ ...prev, lastName: e.target.value }))
                  }
                  placeholder="Enter your last name"
                  className="bg-background border-input text-foreground focus:border-primary focus:ring-primary placeholder:text-muted-foreground"
                />
              )}
            </div>

            {/* Email */}
            <div className="space-y-2">
              <Label htmlFor="email" className="text-muted-foreground flex items-center gap-2">
                <Mail className="h-3.5 w-3.5 text-muted-foreground" />
                Email
              </Label>
              {isLoading ? (
                <Skeleton className="h-10 w-full" />
              ) : (
                <>
                  <Input
                    id="email"
                    name="email"
                    type="email"
                    autoComplete="email"
                    value={profileData.email}
                    onChange={(e) =>
                      setProfileData((prev) => ({ ...prev, email: e.target.value }))
                    }
                    placeholder="you@example.com"
                    className={`bg-background border-input text-foreground focus:border-primary focus:ring-primary placeholder:text-muted-foreground ${
                      !isEmailValid ? "!border-destructive focus:!border-destructive" : ""
                    }`}
                  />
                  {!isEmailValid && (
                    <p className="text-xs text-red-400">Please enter a valid email address</p>
                  )}
                </>
              )}
            </div>

            {/* Username */}
            <div className="space-y-2">
              <Label htmlFor="username" className="text-muted-foreground flex items-center gap-2">
                <AtSign className="h-3.5 w-3.5 text-muted-foreground" />
                Username
              </Label>
              {isLoading ? (
                <Skeleton className="h-10 w-full" />
              ) : (
                <Input
                  id="username"
                  name="username"
                  autoComplete="username"
                  value={profileData.username}
                  onChange={(e) =>
                    setProfileData((prev) => ({ ...prev, username: e.target.value }))
                  }
                  placeholder="your_username"
                  className="bg-background border-input text-foreground focus:border-primary focus:ring-primary placeholder:text-muted-foreground"
                />
              )}
            </div>

            {/* Phone */}
            <div className="space-y-2 md:col-span-2">
              <Label htmlFor="phone" className="text-muted-foreground flex items-center gap-2">
                <Phone className="h-3.5 w-3.5 text-muted-foreground" />
                Phone Number
              </Label>
              {isLoading ? (
                <Skeleton className="h-10 w-full" />
              ) : (
                <>
                  <Input
                    id="phone"
                    name="phone"
                    type="tel"
                    autoComplete="tel"
                    value={profileData.phone}
                    onChange={(e) =>
                      setProfileData((prev) => ({ ...prev, phone: e.target.value }))
                    }
                    placeholder="+1 (555) 123-4567"
                    className={`bg-background border-input text-foreground focus:border-primary focus:ring-primary placeholder:text-muted-foreground md:max-w-md ${
                      !isPhoneValid ? "!border-destructive focus:!border-destructive" : ""
                    }`}
                  />
                  {!isPhoneValid && (
                    <p className="text-xs text-red-400">Please enter a valid phone number</p>
                  )}
                </>
              )}
            </div>
          </div>

          {/* Bio Section */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <Label htmlFor="bio" className="text-muted-foreground flex items-center gap-2">
                <FileText className="h-3.5 w-3.5 text-muted-foreground" />
                Bio
              </Label>
              {!isLoading && (
                <span className={`text-xs ${isBioOverLimit ? "text-destructive" : "text-muted-foreground"}`}>
                  {bioLength}/{BIO_MAX_LENGTH}
                </span>
              )}
            </div>
            {isLoading ? (
              <Skeleton className="h-[120px] w-full" />
            ) : (
              <>
                <Textarea
                  id="bio"
                  value={profileData.bio}
                  onChange={(e) =>
                    setProfileData((prev) => ({ ...prev, bio: e.target.value }))
                  }
                  className={`min-h-[120px] bg-background border-input text-foreground focus:border-primary focus:ring-primary placeholder:text-muted-foreground resize-none ${
                    isBioOverLimit ? "!border-destructive focus:!border-destructive" : ""
                  }`}
                  placeholder="Write a short bio about yourself. This will be visible on your public profile."
                />
                {isBioOverLimit && (
                  <p className="text-xs text-red-400">
                    Bio exceeds maximum length of {BIO_MAX_LENGTH} characters
                  </p>
                )}
              </>
            )}
          </div>
        </CardContent>
        {!isLoading && (
          <CardFooter className="border-t border-border pt-6 flex justify-end bg-accent/5">
            <Button
              onClick={handleSave}
              disabled={!canSaveProfile}
              className="bg-indigo-600 hover:bg-indigo-500 text-white shadow-lg shadow-indigo-500/20 px-8 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isSaving ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Saving...
                </>
              ) : (
                <>
                  <Save className="h-4 w-4 mr-2" />
                  Save Changes
                </>
              )}
            </Button>
          </CardFooter>
        )}
      </Card>
    </div>
  );
}
