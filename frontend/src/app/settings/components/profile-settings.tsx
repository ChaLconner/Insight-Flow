"use client";

import { useRef } from "react";
import Image from "next/image";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { User, Camera } from "lucide-react";
import { getAvatarUrl } from "@/lib/utils";
import { Skeleton } from "@/components/ui/skeleton";

interface ProfileSettingsProps {
    profileData: {
        firstName: string;
        lastName: string;
        email: string;
        username: string;
        phone: string;
        bio: string;
        avatar: string;
    };
    setProfileData: (data: any) => void;
    uploading: boolean;
    onFileChange: (event: React.ChangeEvent<HTMLInputElement>) => void;
    isLoading?: boolean;
}

export function ProfileSettings({
    profileData,
    setProfileData,
    uploading,
    onFileChange,
    isLoading = false
}: ProfileSettingsProps) {
    const fileInputRef = useRef<HTMLInputElement>(null);

    const handleAvatarClick = () => {
        fileInputRef.current?.click();
    };

    return (
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
                            <h3 className="text-lg font-medium text-white">Profile Picture</h3>
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
                                    {uploading ? 'Uploading...' : 'Change Avatar'}
                                </Button>
                            )}
                        </div>
                    </div>

                    <div className="grid gap-4 md:grid-cols-2">
                        <div className="space-y-2">
                            <Label htmlFor="firstName" className="text-zinc-300">First Name</Label>
                            {isLoading ? (
                                <Skeleton className="h-10 w-full" />
                            ) : (
                                <Input
                                    id="firstName"
                                    value={profileData.firstName}
                                    onChange={(e) => setProfileData({ ...profileData, firstName: e.target.value })}
                                    className="form-input !text-zinc-100 bg-zinc-900/50 border-white/10 focus:bg-zinc-900/80 focus:border-indigo-500/50 font-medium placeholder:text-zinc-500"
                                />
                            )}
                        </div>
                        <div className="space-y-2">
                            <Label htmlFor="lastName" className="text-zinc-300">Last Name</Label>
                            {isLoading ? (
                                <Skeleton className="h-10 w-full" />
                            ) : (
                                <Input
                                    id="lastName"
                                    value={profileData.lastName}
                                    onChange={(e) => setProfileData({ ...profileData, lastName: e.target.value })}
                                    className="form-input !text-zinc-100 bg-zinc-900/50 border-white/10 focus:bg-zinc-900/80 focus:border-indigo-500/50 font-medium placeholder:text-zinc-500"
                                />
                            )}
                        </div>
                        <div className="space-y-2">
                            <Label htmlFor="email" className="text-zinc-300">Email</Label>
                            {isLoading ? (
                                <Skeleton className="h-10 w-full" />
                            ) : (
                                <Input
                                    id="email"
                                    type="email"
                                    value={profileData.email}
                                    onChange={(e) => setProfileData({ ...profileData, email: e.target.value })}
                                    className="form-input !text-zinc-100 bg-zinc-900/50 border-white/10 focus:bg-zinc-900/80 focus:border-indigo-500/50 font-medium placeholder:text-zinc-500"
                                />
                            )}
                        </div>
                        <div className="space-y-2">
                            <Label htmlFor="username" className="text-zinc-300">Username</Label>
                            {isLoading ? (
                                <Skeleton className="h-10 w-full" />
                            ) : (
                                <Input
                                    id="username"
                                    value={profileData.username}
                                    onChange={(e) => setProfileData({ ...profileData, username: e.target.value })}
                                    className="form-input !text-zinc-100 bg-zinc-900/50 border-white/10 focus:bg-zinc-900/80 focus:border-indigo-500/50 font-medium placeholder:text-zinc-500"
                                />
                            )}
                        </div>
                        <div className="space-y-2">
                            <Label htmlFor="phone" className="text-zinc-300">Phone</Label>
                            {isLoading ? (
                                <Skeleton className="h-10 w-full" />
                            ) : (
                                <Input
                                    id="phone"
                                    type="tel"
                                    value={profileData.phone}
                                    onChange={(e) => setProfileData({ ...profileData, phone: e.target.value })}
                                    className="form-input !text-zinc-100 bg-zinc-900/50 border-white/10 focus:bg-zinc-900/80 focus:border-indigo-500/50 font-medium placeholder:text-zinc-500"
                                />
                            )}
                        </div>
                    </div>

                    <div className="space-y-2">
                        <Label htmlFor="bio" className="text-zinc-300">Bio</Label>
                        {isLoading ? (
                            <Skeleton className="h-[100px] w-full" />
                        ) : (
                            <textarea
                                id="bio"
                                value={profileData.bio}
                                onChange={(e) => setProfileData({ ...profileData, bio: e.target.value })}
                                className="flex min-h-[100px] w-full rounded-md border border-white/10 bg-zinc-900/50 px-3 py-2 text-sm !text-zinc-100 placeholder:text-zinc-500 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500 disabled:cursor-not-allowed disabled:opacity-50"
                                placeholder="Tell us a little about yourself"
                            />
                        )}
                    </div>
                </CardContent>
            </Card>
        </div>
    );
}
