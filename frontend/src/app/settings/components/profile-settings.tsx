"use client";

import { useRef } from "react";
import Image from "next/image";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { User, Camera, Mail, Phone, AtSign, FileText } from "lucide-react";
import { getAvatarUrl } from "@/lib/utils";
import { Skeleton } from "@/components/ui/skeleton";

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
  profileData: ProfileData;
  setProfileData: React.Dispatch<React.SetStateAction<ProfileData>>;
  uploading: boolean;
  onFileChange: (event: React.ChangeEvent<HTMLInputElement>) => void;
  isLoading?: boolean;
}

// Email validation regex
const EMAIL_REGEX = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

// Phone validation regex (international format)
const PHONE_REGEX = /^[+]?[(]?[0-9]{1,4}[)]?[-\s./0-9]*$/;

// Bio max length
const BIO_MAX_LENGTH = 500;

export function ProfileSettings({
  profileData,
  setProfileData,
  uploading,
  onFileChange,
  isLoading = false,
}: ProfileSettingsProps) {
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleAvatarClick = () => {
    fileInputRef.current?.click();
  };

  // Validation helpers
  const isEmailValid = profileData.email === "" || EMAIL_REGEX.test(profileData.email);
  const isPhoneValid = profileData.phone === "" || PHONE_REGEX.test(profileData.phone);
  const bioLength = profileData.bio.length;
  const isBioOverLimit = bioLength > BIO_MAX_LENGTH;

  return (
    <div className="space-y-6">
      <Card className="glass-card">
        <CardHeader>
          <CardTitle className="text-lg font-semibold text-white flex items-center gap-2">
            <User className="h-5 w-5" />
            Personal Information
          </CardTitle>
          <p className="text-sm text-zinc-400 mt-1">
            Update your personal details and public profile
          </p>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* Avatar Section */}
          <div className="flex flex-col sm:flex-row items-center gap-6 p-4 rounded-xl bg-white/5 border border-white/10">
            <div
              className="relative group cursor-pointer"
              onClick={isLoading ? undefined : handleAvatarClick}
            >
              <div className="relative h-24 w-24 rounded-full overflow-hidden ring-2 ring-white/10 group-hover:ring-indigo-500/50 transition-all duration-300 bg-zinc-800 flex items-center justify-center">
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
                  <User className="h-10 w-10 text-zinc-400" />
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
                onChange={onFileChange}
                disabled={isLoading}
              />
            </div>
            <div className="space-y-2 text-center sm:text-left">
              <h3 className="text-lg font-medium text-white">
                Profile Picture
              </h3>
              <p className="text-sm text-zinc-400">
                PNG, JPG or GIF no bigger than 2MB
              </p>
              {isLoading ? (
                <Skeleton className="h-9 w-32" />
              ) : (
                <Button
                  variant="ghost"
                  size="sm"
                  className="border border-white/10 text-white bg-transparent hover:bg-white/10 transition-all hover:scale-105 active:scale-95"
                  onClick={handleAvatarClick}
                  disabled={uploading}
                >
                  {uploading ? "Uploading..." : "Change Avatar"}
                </Button>
              )}
            </div>
          </div>

          {/* Form Fields */}
          <div className="grid gap-5 md:grid-cols-2">
            {/* First Name */}
            <div className="space-y-2">
              <Label htmlFor="firstName" className="text-zinc-300 flex items-center gap-2">
                <User className="h-3.5 w-3.5 text-zinc-500" />
                First Name
              </Label>
              {isLoading ? (
                <Skeleton className="h-10 w-full" />
              ) : (
                <Input
                  id="firstName"
                  value={profileData.firstName}
                  onChange={(e) =>
                    setProfileData((prev) => ({
                      ...prev,
                      firstName: e.target.value,
                    }))
                  }
                  placeholder="Enter your first name"
                  className="form-input !text-zinc-100 bg-zinc-900/50 border-white/10 focus:bg-zinc-900/80 focus:border-indigo-500/50 font-medium placeholder:text-zinc-500"
                />
              )}
            </div>

            {/* Last Name */}
            <div className="space-y-2">
              <Label htmlFor="lastName" className="text-zinc-300 flex items-center gap-2">
                <User className="h-3.5 w-3.5 text-zinc-500" />
                Last Name
              </Label>
              {isLoading ? (
                <Skeleton className="h-10 w-full" />
              ) : (
                <Input
                  id="lastName"
                  value={profileData.lastName}
                  onChange={(e) =>
                    setProfileData((prev) => ({ ...prev, lastName: e.target.value }))
                  }
                  placeholder="Enter your last name"
                  className="form-input !text-zinc-100 bg-zinc-900/50 border-white/10 focus:bg-zinc-900/80 focus:border-indigo-500/50 font-medium placeholder:text-zinc-500"
                />
              )}
            </div>

            {/* Email */}
            <div className="space-y-2">
              <Label htmlFor="email" className="text-zinc-300 flex items-center gap-2">
                <Mail className="h-3.5 w-3.5 text-zinc-500" />
                Email
              </Label>
              {isLoading ? (
                <Skeleton className="h-10 w-full" />
              ) : (
                <>
                  <Input
                    id="email"
                    type="email"
                    value={profileData.email}
                    onChange={(e) =>
                      setProfileData((prev) => ({ ...prev, email: e.target.value }))
                    }
                    placeholder="you@example.com"
                    className={`form-input !text-zinc-100 bg-zinc-900/50 border-white/10 focus:bg-zinc-900/80 focus:border-indigo-500/50 font-medium placeholder:text-zinc-500 ${
                      !isEmailValid ? "!border-red-500/50 focus:!border-red-500" : ""
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
              <Label htmlFor="username" className="text-zinc-300 flex items-center gap-2">
                <AtSign className="h-3.5 w-3.5 text-zinc-500" />
                Username
              </Label>
              {isLoading ? (
                <Skeleton className="h-10 w-full" />
              ) : (
                <Input
                  id="username"
                  value={profileData.username}
                  onChange={(e) =>
                    setProfileData((prev) => ({ ...prev, username: e.target.value }))
                  }
                  placeholder="your_username"
                  className="form-input !text-zinc-100 bg-zinc-900/50 border-white/10 focus:bg-zinc-900/80 focus:border-indigo-500/50 font-medium placeholder:text-zinc-500"
                />
              )}
            </div>

            {/* Phone */}
            <div className="space-y-2 md:col-span-2">
              <Label htmlFor="phone" className="text-zinc-300 flex items-center gap-2">
                <Phone className="h-3.5 w-3.5 text-zinc-500" />
                Phone Number
              </Label>
              {isLoading ? (
                <Skeleton className="h-10 w-full" />
              ) : (
                <>
                  <Input
                    id="phone"
                    type="tel"
                    value={profileData.phone}
                    onChange={(e) =>
                      setProfileData((prev) => ({ ...prev, phone: e.target.value }))
                    }
                    placeholder="+1 (555) 123-4567"
                    className={`form-input !text-zinc-100 bg-zinc-900/50 border-white/10 focus:bg-zinc-900/80 focus:border-indigo-500/50 font-medium placeholder:text-zinc-500 md:max-w-md ${
                      !isPhoneValid ? "!border-red-500/50 focus:!border-red-500" : ""
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
              <Label htmlFor="bio" className="text-zinc-300 flex items-center gap-2">
                <FileText className="h-3.5 w-3.5 text-zinc-500" />
                Bio
              </Label>
              {!isLoading && (
                <span className={`text-xs ${isBioOverLimit ? "text-red-400" : "text-zinc-500"}`}>
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
                  className={`min-h-[120px] !text-zinc-100 bg-zinc-900/50 border-white/10 focus:bg-zinc-900/80 focus:border-indigo-500/50 placeholder:text-zinc-500 resize-none ${
                    isBioOverLimit ? "!border-red-500/50 focus:!border-red-500" : ""
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
      </Card>
    </div>
  );
}
