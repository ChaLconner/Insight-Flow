import React, { useState, useEffect } from "react";
import Image from "next/image";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { X, Users, Settings, Save, Loader2 } from "lucide-react";
import {
  type Project,
  ProjectStatus,
  type CreateProjectRequest,
  type UpdateProjectRequest,
  type User,
} from "@/types";
// import { apiClient } from "@/lib/api-client";
import { getAvatarUrl } from "@/lib/utils";
import { toast } from "sonner";
import { getErrorMessage } from "@/lib/error-utils";
import { UserSearchSelect } from "@/components/ui/user-search-select";
import { CustomSelect } from "@/components/ui/custom-select";

interface ProjectModalProps {
  isOpen: boolean;
  onClose: () => void;
  project?: Project | null;
  mode: "create" | "edit";
  onSubmit: (
    data: CreateProjectRequest | UpdateProjectRequest,
  ) => Promise<void>;
}

const projectColors = [
  "#6366f1", // indigo
  "#10b981", // emerald
  "#f59e0b", // amber
  "#ef4444", // red
  "#8b5cf6", // violet
  "#06b6d4", // cyan
  "#84cc16", // lime
  "#f97316", // orange
];

export function ProjectModal({
  isOpen,
  onClose,
  project,
  mode,
  onSubmit,
}: ProjectModalProps) {
  // No longer fetching all users on mount

  // Fetch users when component mounts
  // No longer fetching all users on mount
  const [selectedUsers, setSelectedUsers] = useState<User[]>([]);

  const [formData, setFormData] = useState({
    name: project?.name ?? "",
    description: project?.description ?? "",
    color: project?.color ?? projectColors[0],
    status: project?.status ?? ProjectStatus.ACTIVE,
    memberIds: project?.members?.map((m) => m.userId) ?? [],
    settings: {
      allowPublicAccess: project?.settings?.allowPublicAccess ?? false,
      requireApproval: project?.settings?.requireApproval ?? true,
      defaultTaskVisibility: project?.settings?.defaultTaskVisibility ?? "team",
      notificationSettings: {
        taskAssigned:
          project?.settings?.notificationSettings?.taskAssigned ?? true,
        statusChanged:
          project?.settings?.notificationSettings?.statusChanged ?? true,
        deadlineApproaching:
          project?.settings?.notificationSettings?.deadlineApproaching ?? true,
        commentAdded:
          project?.settings?.notificationSettings?.commentAdded ?? true,
      },
    },
  });

  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errors, setErrors] = useState<Record<string, string>>({});

  // Update form data when project prop changes in edit mode
  useEffect(() => {
    if (project && mode === "edit") {
      setFormData({
        name: project.name ?? "",
        description: project.description ?? "",
        color: project.color ?? projectColors[0],
        status: project.status ?? ProjectStatus.ACTIVE,
        memberIds: project.members?.map((m) => m.userId) ?? [],
        settings: {
          allowPublicAccess: project.settings?.allowPublicAccess ?? false,
          requireApproval: project.settings?.requireApproval ?? true,
          defaultTaskVisibility:
            project.settings?.defaultTaskVisibility ?? "team",
          notificationSettings: {
            taskAssigned:
              project.settings?.notificationSettings?.taskAssigned ?? true,
            statusChanged:
              project.settings?.notificationSettings?.statusChanged ?? true,
            deadlineApproaching:
              project.settings?.notificationSettings?.deadlineApproaching ??
              true,
            commentAdded:
              project.settings?.notificationSettings?.commentAdded ?? true,
          },
        },
      });

      // Populate selected users from project members
      // The member object structure from ProjectsPage seems to have a nested 'user' object or spreads user props
      // We need to map it back to User type.
      // Based on ProjectsPage, member has a .user property with full user details.
      const members = project.members || [];
      const users: User[] = members.map((m) => {
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        const member = m as any;
        return (
          member.user ?? {
            id: member.userId,
            firstName: member.name?.split(" ")[0] ?? "Unknown",
            lastName: member.name?.split(" ").slice(1).join(" ") ?? "User",
            email: member.email ?? "",
            username: "unknown",
            role: "user",
            avatar: member.avatar,
            isActive: true,
            emailVerified: true,
            createdAt: new Date().toISOString(),
            updatedAt: new Date().toISOString(),
          }
        );
      });
      setSelectedUsers(users);
    } else if (mode === "create") {
      // Reset form for create mode
      setFormData({
        name: "",
        description: "",
        color: projectColors[0],
        status: ProjectStatus.ACTIVE,
        memberIds: [],
        settings: {
          allowPublicAccess: false,
          requireApproval: true,
          defaultTaskVisibility: "team",
          notificationSettings: {
            taskAssigned: true,
            statusChanged: true,
            deadlineApproaching: true,
            commentAdded: true,
          },
        },
      });
      setSelectedUsers([]);
    }
  }, [project, mode]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    setErrors({});

    // Validation
    const newErrors: Record<string, string> = {};
    if (!formData.name.trim()) {
      newErrors.name = "Project name is required";
    }

    if (Object.keys(newErrors).length > 0) {
      setErrors(newErrors);
      setIsSubmitting(false);
      return;
    }

    try {
      const submitData =
        mode === "create"
          ? {
              name: formData.name,
              description: formData.description,
              color: formData.color,
              memberIds: formData.memberIds,
              settings: formData.settings,
            }
          : {
              name: formData.name,
              description: formData.description,
              color: formData.color,
              status: formData.status,
              memberIds: formData.memberIds,
              settings: formData.settings,
            };

      await onSubmit(submitData);

      const action = mode === "create" ? "created" : "updated";
      toast.success(`Project ${action} successfully`, {
        description: `Project "${formData.name}" has been ${action}.`,
      });

      onClose();
    } catch (error) {
      console.error("Error submitting project:", error);
      toast.error(
        mode === "create"
          ? "Failed to create project"
          : "Failed to update project",
        {
          description: getErrorMessage(error),
        },
      );
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleInputChange = (field: string, value: unknown) => {
    setFormData((prev) => ({ ...prev, [field]: value }));
    if (errors[field]) {
      setErrors((prev) => ({ ...prev, [field]: "" }));
    }
  };

  const handleMemberToggle = (userId: string) => {
    setFormData((prev) => ({
      ...prev,
      memberIds: prev.memberIds.includes(userId)
        ? prev.memberIds.filter((id) => id !== userId)
        : [...prev.memberIds, userId],
    }));
  };

  if (!isOpen) {
    return null;
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/50 backdrop-blur-sm"
        onClick={onClose}
      />

      {/* Modal */}
      <Card className="relative w-full max-w-2xl max-h-[90vh] overflow-y-auto border-white/10 bg-zinc-900/95 backdrop-blur-xl shadow-2xl">
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-6">
          <CardTitle className="text-xl font-semibold text-white">
            {mode === "create" ? "Create New Project" : "Edit Project"}
          </CardTitle>
          <Button
            variant="ghost"
            size="sm"
            onClick={onClose}
            className="h-8 w-8 p-0 text-zinc-400 hover:text-white"
          >
            <X className="h-4 w-4" />
          </Button>
        </CardHeader>

        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-6">
            {/* Basic Information */}
            <div className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="name" className="text-zinc-300">
                  Project Name *
                </Label>
                <Input
                  id="name"
                  value={formData.name}
                  onChange={(e) => handleInputChange("name", e.target.value)}
                  placeholder="Enter project name"
                  className={`bg-white/5 border-white/10 text-white placeholder:text-zinc-400 ${
                    errors.name ? "border-red-500" : ""
                  }`}
                  disabled={isSubmitting}
                />
                {errors.name && (
                  <p className="text-sm text-red-400">{errors.name}</p>
                )}
              </div>

              <div className="space-y-2">
                <Label htmlFor="description" className="text-zinc-300">
                  Description
                </Label>
                <textarea
                  id="description"
                  rows={3}
                  value={formData.description}
                  onChange={(e) =>
                    handleInputChange("description", e.target.value)
                  }
                  placeholder="Describe your project..."
                  className="w-full rounded-lg bg-white/5 border border-white/10 px-3 py-2 text-white placeholder:text-zinc-400"
                  disabled={isSubmitting}
                  style={{ resize: "vertical" }}
                />
              </div>

              <div className="space-y-2">
                <Label className="text-zinc-300">Project Color</Label>
                <div className="flex gap-2 flex-wrap">
                  {projectColors.map((color) => (
                    <button
                      key={color}
                      type="button"
                      onClick={() => handleInputChange("color", color)}
                      className={`h-8 w-8 rounded-lg border-2 transition-all cursor-pointer ${
                        formData.color === color
                          ? "border-white scale-110"
                          : "border-white/20 hover:border-white/40"
                      }`}
                      style={{ backgroundColor: color }}
                      disabled={isSubmitting}
                    />
                  ))}
                </div>
              </div>
            </div>

            {/* Team Members */}
            <div className="space-y-3">
              <Label className="text-zinc-300 flex items-center gap-2">
                <Users className="h-4 w-4" />
                Team Members
              </Label>

              {/* Search User Input */}
              <div className="relative">
                <UserSearchSelect
                  value=""
                  onChange={() => {}} // Controlled by onUserSelect
                  onUserSelect={(user) => {
                    if (!formData.memberIds.includes(user.id)) {
                      handleMemberToggle(user.id);
                      // Add to selectedUsers if not present (logic handled in toggle or separate effect,
                      // but simpler to just add here locally since we have the full user object)
                      setSelectedUsers((prev) => [...prev, user]);
                    } else {
                      toast.info("User already added");
                    }
                  }}
                  placeholder="Search to add team members..."
                />
              </div>

              {/* Selected Users List */}
              <div className="space-y-2 mt-2">
                {selectedUsers.length === 0 && (
                  <p className="text-sm text-zinc-500 italic">
                    No members added yet.
                  </p>
                )}
                {selectedUsers.map((user) => (
                  <div
                    key={user.id}
                    className="flex items-center justify-between p-2 rounded-lg bg-white/5 border border-white/10"
                  >
                    <div className="flex items-center gap-3">
                      {/* Avatar */}
                      <div className="relative h-8 w-8 rounded-full bg-zinc-700 border border-white/10 flex items-center justify-center overflow-hidden shrink-0">
                        {user.avatar ? (
                          <Image
                            src={getAvatarUrl(user.avatar)}
                            alt={`${user.firstName} ${user.lastName}`}
                            fill
                            className="object-cover"
                            sizes="32px"
                          />
                        ) : null}
                        <span
                          className={`text-xs font-medium text-zinc-300 ${user.avatar ? "hidden" : ""}`}
                        >
                          {user.firstName && typeof user.firstName === "string"
                            ? user.firstName[0]
                            : ""}
                          {user.lastName && typeof user.lastName === "string"
                            ? user.lastName[0]
                            : ""}
                        </span>
                      </div>
                      <div>
                        <p className="text-white text-sm font-medium">
                          {user.firstName} {user.lastName}
                        </p>
                        <p className="text-zinc-400 text-xs">{user.email}</p>
                      </div>
                    </div>
                    <Button
                      type="button"
                      variant="ghost"
                      size="sm"
                      onClick={() => {
                        handleMemberToggle(user.id);
                        setSelectedUsers((prev) =>
                          prev.filter((u) => u.id !== user.id),
                        );
                      }}
                      className="h-8 w-8 p-0 text-zinc-400 hover:text-red-400 hover:bg-red-400/10"
                    >
                      <X className="h-4 w-4" />
                    </Button>
                  </div>
                ))}
              </div>
            </div>

            {/* Project Settings */}
            <div className="space-y-4">
              <Label className="text-zinc-300 flex items-center gap-2">
                <Settings className="h-4 w-4" />
                Project Settings
              </Label>

              <div className="space-y-3 pl-4 border-l border-white/10">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-white text-sm font-medium">
                      Allow Public Access
                    </p>
                    <p className="text-zinc-400 text-xs">
                      Anyone with the link can view
                    </p>
                  </div>
                  <label className="relative inline-flex items-center cursor-pointer">
                    <input
                      type="checkbox"
                      checked={formData.settings.allowPublicAccess}
                      onChange={(e) =>
                        handleInputChange("settings", {
                          ...formData.settings,
                          allowPublicAccess: e.target.checked,
                        })
                      }
                      className="sr-only peer"
                      disabled={isSubmitting}
                    />
                    <div className="w-11 h-6 bg-white/10 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-indigo-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-white after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-indigo-600"></div>
                  </label>
                </div>

                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-white text-sm font-medium">
                      Require Approval
                    </p>
                    <p className="text-zinc-400 text-xs">
                      Members need approval to join
                    </p>
                  </div>
                  <label className="relative inline-flex items-center cursor-pointer">
                    <input
                      type="checkbox"
                      checked={formData.settings.requireApproval}
                      onChange={(e) =>
                        handleInputChange("settings", {
                          ...formData.settings,
                          requireApproval: e.target.checked,
                        })
                      }
                      className="sr-only peer"
                      disabled={isSubmitting}
                    />
                    <div className="w-11 h-6 bg-white/10 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-indigo-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-white after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-indigo-600"></div>
                  </label>
                </div>

                <div className="space-y-2">
                  <Label className="text-zinc-400 text-xs">
                    Default Task Visibility
                  </Label>
                  <CustomSelect
                    value={formData.settings.defaultTaskVisibility}
                    onChange={(value) =>
                      handleInputChange("settings", {
                        ...formData.settings,
                        defaultTaskVisibility: value,
                      })
                    }
                    options={[
                      {
                        value: "private",
                        label: "Private",
                        description: "Only members can see tasks",
                      },
                      {
                        value: "team",
                        label: "Team",
                        description: "All team members can see tasks",
                      },
                      {
                        value: "public",
                        label: "Public",
                        description: "Anyone with link can see tasks",
                      },
                    ]}
                    className="w-full"
                  />
                </div>
              </div>
            </div>

            {/* Actions */}
            <div className="flex gap-3 pt-6 border-t border-white/10">
              <Button
                type="button"
                variant="outline"
                onClick={onClose}
                className="flex-1 border-white/10 text-white hover:bg-white/5"
                disabled={isSubmitting}
              >
                Cancel
              </Button>
              <Button
                type="submit"
                className="flex-1 bg-indigo-600 hover:bg-indigo-500 text-white"
                disabled={isSubmitting}
              >
                {isSubmitting ? (
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                ) : (
                  <Save className="h-4 w-4 mr-2" />
                )}
                {mode === "create" ? "Create Project" : "Update Project"}
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
