"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Key, Eye, EyeOff, Shield } from "lucide-react";
import { toast } from "sonner";

interface SecuritySettingsProps {
    currentPassword: string;
    setCurrentPassword: (val: string) => void;
    newPassword: string;
    setNewPassword: (val: string) => void;
    confirmPassword: string;
    setConfirmPassword: (val: string) => void;
    passwordStrength: number;
    showPassword: boolean;
    setShowPassword: (val: boolean) => void;
    saving: boolean;
    onUpdatePassword: () => void;
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
    onUpdatePassword
}: SecuritySettingsProps) {
    return (
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
                        <Label htmlFor="currentPassword" className="text-zinc-300">Current Password</Label>
                        <div className="relative">
                            <Input
                                id="currentPassword"
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
                        <Label htmlFor="newPassword" className="text-zinc-300">New Password</Label>
                        <div className="relative">
                            <Input
                                id="newPassword"
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
                        <Label htmlFor="confirmPassword" className="text-zinc-300">Confirm Password</Label>
                        <div className="relative">
                            <Input
                                id="confirmPassword"
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
                        onClick={onUpdatePassword}
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
}
