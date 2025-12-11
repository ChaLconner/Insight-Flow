"use client";

import type { Dispatch, SetStateAction } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Eye, EyeOff, Lock, Key } from "lucide-react";

interface SecuritySettingsProps {
    currentPassword: string;
    setCurrentPassword: Dispatch<SetStateAction<string>>;
    newPassword: string;
    setNewPassword: Dispatch<SetStateAction<string>>;
    confirmPassword: string;
    setConfirmPassword: Dispatch<SetStateAction<string>>;
    passwordStrength: number;
    showPassword: boolean;
    setShowPassword: Dispatch<SetStateAction<boolean>>;
    saving: boolean;
    onUpdatePassword: () => Promise<void>;
}

export function SecuritySettings({
    currentPassword,
    setCurrentPassword,
    newPassword,
    setNewPassword,
    confirmPassword,
    setConfirmPassword,
    passwordStrength,
    showPassword,
    setShowPassword,
    saving,
    onUpdatePassword,
}: SecuritySettingsProps) {
    const getStrengthColor = (strength: number) => {
        if (strength <= 25) {return "bg-red-500";}
        if (strength <= 50) {return "bg-orange-500";}
        if (strength <= 75) {return "bg-yellow-500";}
        return "bg-green-500";
    };

    const getStrengthLabel = (strength: number) => {
        if (strength <= 25) {return "Weak";}
        if (strength <= 50) {return "Fair";}
        if (strength <= 75) {return "Good";}
        return "Strong";
    };

    return (
        <div className="space-y-6">
            {/* Password Change Section */}
            <Card className="glass-card">
                <CardHeader>
                    <div className="flex items-center gap-3">
                        <div className="p-2 rounded-lg bg-indigo-500/10">
                            <Lock className="h-5 w-5 text-indigo-400" />
                        </div>
                        <div>
                            <CardTitle className="text-white">Change Password</CardTitle>
                            <CardDescription>Update your password to keep your account secure</CardDescription>
                        </div>
                    </div>
                </CardHeader>
                <CardContent className="space-y-4">
                    {/* Hidden input to trick browser autofill into thinking this is the username field for the password inputs below.
                        Using position:absolute/opacity:0 instead of display:none because some browsers ignore display:none inputs for autofill logic. */}
                    <input
                        type="text"
                        name="username"
                        autoComplete="username"
                        style={{ position: 'absolute', opacity: 0, height: 0, width: 0, padding: 0, margin: 0, border: 'none' }}
                        tabIndex={-1}
                        aria-hidden="true"
                    />

                    <div className="space-y-2">
                        <Label htmlFor="currentPassword" className="text-zinc-300">Current Password</Label>
                        <div className="relative">
                            <Input
                                id="currentPassword"
                                type={showPassword ? "text" : "password"}
                                value={currentPassword}
                                onChange={(e) => setCurrentPassword(e.target.value)}
                                autoComplete="current-password"
                                autoCorrect="off"
                                autoCapitalize="off"
                                spellCheck={false}
                                data-1p-ignore="true"
                                data-lpignore="true"
                                data-form-type="other"
                                className="bg-zinc-800/50 border-white/10 text-white pr-10 autofill:bg-zinc-800/50 autofill:text-white [-webkit-autofill]:bg-zinc-800/50 [-webkit-autofill]:text-white [&:-webkit-autofill]:!bg-zinc-800/50 [&:-webkit-autofill]:!text-white [&:-webkit-autofill]:[-webkit-text-fill-color:white]"
                                placeholder="Enter current password"
                            />
                            <button
                                type="button"
                                onClick={() => setShowPassword(!showPassword)}
                                className="absolute right-3 top-1/2 -translate-y-1/2 text-zinc-400 hover:text-white transition-colors"
                            >
                                {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                            </button>
                        </div>
                    </div>

                    <div className="space-y-2">
                        <Label htmlFor="newPassword" className="text-zinc-300">New Password</Label>
                        <div className="relative">
                            <Input
                                id="newPassword"
                                type={showPassword ? "text" : "password"}
                                value={newPassword}
                                onChange={(e) => setNewPassword(e.target.value)}
                                autoComplete="new-password"
                                autoCorrect="off"
                                autoCapitalize="off"
                                spellCheck={false}
                                data-1p-ignore="true"
                                data-lpignore="true"
                                className="bg-zinc-800/50 border-white/10 text-white pr-10 [&:-webkit-autofill]:!bg-zinc-800/50 [&:-webkit-autofill]:[-webkit-text-fill-color:white]"
                                placeholder="Enter new password"
                            />
                        </div>
                        {newPassword && (
                            <div className="space-y-2">
                                <div className="flex items-center gap-2">
                                    <div className="flex-1 h-2 bg-zinc-700 rounded-full overflow-hidden">
                                        <div
                                            className={`h-full transition-all duration-300 ${getStrengthColor(passwordStrength)}`}
                                            style={{ width: `${passwordStrength}%` }}
                                        />
                                    </div>
                                    <span className="text-xs text-zinc-400">
                                        {getStrengthLabel(passwordStrength)}
                                    </span>
                                </div>
                                <ul className="text-xs text-zinc-500 space-y-1">
                                    <li className={newPassword.length >= 8 ? "text-green-400" : ""}>
                                        • At least 8 characters
                                    </li>
                                    <li className={/[A-Z]/.test(newPassword) ? "text-green-400" : ""}>
                                        • At least one uppercase letter
                                    </li>
                                    <li className={/[a-z]/.test(newPassword) ? "text-green-400" : ""}>
                                        • At least one lowercase letter
                                    </li>
                                    <li className={/[0-9]/.test(newPassword) ? "text-green-400" : ""}>
                                        • At least one number
                                    </li>
                                </ul>
                            </div>
                        )}
                    </div>

                    <div className="space-y-2">
                        <Label htmlFor="confirmPassword" className="text-zinc-300">Confirm New Password</Label>
                        <Input
                            id="confirmPassword"
                            type={showPassword ? "text" : "password"}
                            value={confirmPassword}
                            onChange={(e) => setConfirmPassword(e.target.value)}
                            autoComplete="new-password"
                            className="bg-zinc-800/50 border-white/10 text-white"
                            placeholder="Confirm new password"
                        />
                        {confirmPassword && newPassword !== confirmPassword && (
                            <p className="text-xs text-red-400">Passwords do not match</p>
                        )}
                    </div>

                    <Button
                        onClick={onUpdatePassword}
                        disabled={saving || !currentPassword || !newPassword || !confirmPassword || newPassword !== confirmPassword}
                        className="bg-indigo-600 hover:bg-indigo-500 text-white w-full sm:w-auto"
                    >
                        <Key className="h-4 w-4 mr-2" />
                        {saving ? "Updating..." : "Update Password"}
                    </Button>
                </CardContent>
            </Card>

            {/* Active Sessions Section */}
            <Card className="glass-card">
                <CardHeader>
                    <CardTitle className="text-white">Active Sessions</CardTitle>
                    <CardDescription>Manage devices where you&apos;re currently logged in</CardDescription>
                </CardHeader>
                <CardContent>
                    <div className="bg-zinc-800/50 rounded-lg p-4 border border-white/10">
                        <div className="flex items-center justify-between">
                            <div>
                                <p className="text-white font-medium">Current Session</p>
                                <p className="text-zinc-400 text-sm">This device • Active now</p>
                            </div>
                            <span className="px-2 py-1 bg-green-500/20 text-green-400 text-xs rounded-full">
                                Active
                            </span>
                        </div>
                    </div>
                </CardContent>
            </Card>
        </div>
    );
}
