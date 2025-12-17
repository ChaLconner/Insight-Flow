"use client";

import { useState } from "react";
import type { Dispatch, SetStateAction } from "react";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { 
  Eye, 
  EyeOff, 
  Lock, 
  Key, 
  Monitor, 
  Smartphone, 
  Shield,
  CheckCircle2,
  XCircle,
  AlertCircle
} from "lucide-react";

// ===================================
// Type Definitions
// ===================================

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

interface PasswordRequirement {
  label: string;
  test: (password: string) => boolean;
}

// ===================================
// Password Requirements Configuration  
// ===================================

const passwordRequirements: PasswordRequirement[] = [
  { label: "At least 8 characters", test: (p) => p.length >= 8 },
  { label: "At least one uppercase letter", test: (p) => /[A-Z]/.test(p) },
  { label: "At least one lowercase letter", test: (p) => /[a-z]/.test(p) },
  { label: "At least one number", test: (p) => /[0-9]/.test(p) },
];

// ===================================
// Component
// ===================================

export function SecuritySettings({
  currentPassword,
  setCurrentPassword,
  newPassword,
  setNewPassword,
  confirmPassword,
  setConfirmPassword,
  passwordStrength,
  // Unused in this component as we have separate show/hide states per field
  showPassword: _showPassword,
  setShowPassword: _setShowPassword,
  saving,
  onUpdatePassword,
}: SecuritySettingsProps) {
  // Separate show/hide states for each field
  const [showCurrentPassword, setShowCurrentPassword] = useState(false);
  const [showNewPassword, setShowNewPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);

  const getStrengthColor = (strength: number) => {
    if (strength <= 25) {
      return "bg-red-500";
    }
    if (strength <= 50) {
      return "bg-orange-500";
    }
    if (strength <= 75) {
      return "bg-yellow-500";
    }
    return "bg-green-500";
  };

  const getStrengthLabel = (strength: number) => {
    if (strength <= 25) {
      return { text: "Weak", color: "text-red-400" };
    }
    if (strength <= 50) {
      return { text: "Fair", color: "text-orange-400" };
    }
    if (strength <= 75) {
      return { text: "Good", color: "text-yellow-400" };
    }
    return { text: "Strong", color: "text-green-400" };
  };

  const passwordsMatch = confirmPassword === "" || newPassword === confirmPassword;
  const canSubmit = 
    currentPassword.length > 0 && 
    newPassword.length > 0 && 
    confirmPassword.length > 0 && 
    newPassword === confirmPassword &&
    passwordStrength >= 50;

  const strengthInfo = getStrengthLabel(passwordStrength);

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
              <CardDescription>
                Update your password to keep your account secure
              </CardDescription>
            </div>
          </div>
        </CardHeader>
        <CardContent className="space-y-5">
          {/* Current Password */}
          <div className="space-y-2">
            <Label htmlFor="currentPassword" className="text-zinc-300 flex items-center gap-2">
              <Key className="h-3.5 w-3.5 text-zinc-500" />
              Current Password
            </Label>
            <div className="relative">
              <Input
                id="currentPassword"
                type={showCurrentPassword ? "text" : "password"}
                value={currentPassword}
                onChange={(e) => setCurrentPassword(e.target.value)}
                autoComplete="current-password"
                autoCorrect="off"
                autoCapitalize="off"
                spellCheck={false}
                className="bg-zinc-800/50 border-white/10 text-white pr-10"
                placeholder="Enter current password"
              />
              <button
                type="button"
                onClick={() => setShowCurrentPassword(!showCurrentPassword)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-zinc-400 hover:text-white transition-colors"
                aria-label={showCurrentPassword ? "Hide password" : "Show password"}
              >
                {showCurrentPassword ? (
                  <EyeOff className="h-4 w-4" />
                ) : (
                  <Eye className="h-4 w-4" />
                )}
              </button>
            </div>
          </div>

          {/* New Password */}
          <div className="space-y-2">
            <Label htmlFor="newPassword" className="text-zinc-300 flex items-center gap-2">
              <Lock className="h-3.5 w-3.5 text-zinc-500" />
              New Password
            </Label>
            <div className="relative">
              <Input
                id="newPassword"
                type={showNewPassword ? "text" : "password"}
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                autoComplete="new-password"
                autoCorrect="off"
                autoCapitalize="off"
                spellCheck={false}
                className="bg-zinc-800/50 border-white/10 text-white pr-10"
                placeholder="Enter new password"
              />
              <button
                type="button"
                onClick={() => setShowNewPassword(!showNewPassword)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-zinc-400 hover:text-white transition-colors"
                aria-label={showNewPassword ? "Hide password" : "Show password"}
              >
                {showNewPassword ? (
                  <EyeOff className="h-4 w-4" />
                ) : (
                  <Eye className="h-4 w-4" />
                )}
              </button>
            </div>

            {/* Password Strength Indicator */}
            {newPassword && (
              <div className="space-y-3 mt-3 p-4 rounded-lg bg-zinc-800/30 border border-white/5">
                {/* Strength Bar */}
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-xs text-zinc-400">Password Strength</span>
                    <span className={`text-xs font-medium ${strengthInfo.color}`}>
                      {strengthInfo.text}
                    </span>
                  </div>
                  <div className="h-2 bg-zinc-700 rounded-full overflow-hidden">
                    <div
                      className={`h-full transition-all duration-300 ${getStrengthColor(passwordStrength)}`}
                      style={{ width: `${passwordStrength}%` }}
                    />
                  </div>
                </div>

                {/* Requirements Checklist */}
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                  {passwordRequirements.map((req, index) => {
                    const passed = req.test(newPassword);
                    return (
                      <div 
                        key={index}
                        className={`flex items-center gap-2 text-xs ${
                          passed ? "text-green-400" : "text-zinc-500"
                        }`}
                      >
                        {passed ? (
                          <CheckCircle2 className="h-3.5 w-3.5" />
                        ) : (
                          <XCircle className="h-3.5 w-3.5" />
                        )}
                        <span>{req.label}</span>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}
          </div>

          {/* Confirm Password */}
          <div className="space-y-2">
            <Label htmlFor="confirmPassword" className="text-zinc-300 flex items-center gap-2">
              <Shield className="h-3.5 w-3.5 text-zinc-500" />
              Confirm New Password
            </Label>
            <div className="relative">
              <Input
                id="confirmPassword"
                type={showConfirmPassword ? "text" : "password"}
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                autoComplete="new-password"
                className={`bg-zinc-800/50 border-white/10 text-white pr-10 ${
                  !passwordsMatch ? "!border-red-500/50 focus:!border-red-500" : ""
                }`}
                placeholder="Confirm new password"
              />
              <button
                type="button"
                onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-zinc-400 hover:text-white transition-colors"
                aria-label={showConfirmPassword ? "Hide password" : "Show password"}
              >
                {showConfirmPassword ? (
                  <EyeOff className="h-4 w-4" />
                ) : (
                  <Eye className="h-4 w-4" />
                )}
              </button>
            </div>
            {!passwordsMatch && (
              <p className="text-xs text-red-400 flex items-center gap-1">
                <AlertCircle className="h-3 w-3" />
                Passwords do not match
              </p>
            )}
          </div>

          {/* Submit Button */}
          <div className="pt-2">
            <Button
              onClick={onUpdatePassword}
              disabled={saving || !canSubmit}
              className="bg-indigo-600 hover:bg-indigo-500 text-white w-full sm:w-auto"
            >
              <Key className="h-4 w-4 mr-2" />
              {saving ? "Updating..." : "Update Password"}
            </Button>
            {!canSubmit && newPassword.length > 0 && passwordStrength < 50 && (
              <p className="text-xs text-amber-400 mt-2 flex items-center gap-1">
                <AlertCircle className="h-3 w-3" />
                Password strength must be at least Fair to continue
              </p>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Active Sessions Section */}
      <Card className="glass-card">
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="text-white">Active Sessions</CardTitle>
              <CardDescription>
                Manage devices where you&apos;re currently logged in
              </CardDescription>
            </div>
          </div>
        </CardHeader>
        <CardContent className="space-y-3">
          {/* Current Session */}
          <div className="bg-zinc-800/50 rounded-lg p-4 border border-emerald-500/20">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-lg bg-emerald-500/10">
                  <Monitor className="h-5 w-5 text-emerald-400" />
                </div>
                <div>
                  <p className="text-white font-medium flex items-center gap-2">
                    Current Session
                    <span className="px-2 py-0.5 bg-emerald-500/20 text-emerald-400 text-xs rounded-full">
                      Active
                    </span>
                  </p>
                  <p className="text-zinc-400 text-sm">
                    This device • Active now
                  </p>
                </div>
              </div>
            </div>
          </div>

          {/* Info Message */}
          <div className="flex items-start gap-3 p-4 rounded-lg bg-zinc-800/30 border border-white/5">
            <AlertCircle className="h-4 w-4 text-zinc-500 mt-0.5 flex-shrink-0" />
            <div className="text-xs text-zinc-500">
              <p>Session management across multiple devices is coming soon.</p>
              <p className="mt-1">You&apos;ll be able to view and revoke access from any device.</p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Two-Factor Authentication Placeholder */}
      <Card className="glass-card border-amber-500/10">
        <CardHeader>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-lg bg-amber-500/10">
                <Smartphone className="h-5 w-5 text-amber-400" />
              </div>
              <div>
                <CardTitle className="text-white flex items-center gap-2">
                  Two-Factor Authentication
                  <span className="px-2 py-0.5 bg-amber-500/20 text-amber-400 text-xs rounded-full">
                    Coming Soon
                  </span>
                </CardTitle>
                <CardDescription>
                  Add an extra layer of security to your account
                </CardDescription>
              </div>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <div className="flex items-start gap-3 p-4 rounded-lg bg-amber-500/5 border border-amber-500/10">
            <Shield className="h-4 w-4 text-amber-400 mt-0.5 flex-shrink-0" />
            <div className="text-xs text-zinc-400">
              <p>Two-factor authentication adds an additional layer of security by requiring a verification code from your phone when signing in.</p>
              <p className="mt-2 text-amber-400/80">This feature is currently in development and will be available soon.</p>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
