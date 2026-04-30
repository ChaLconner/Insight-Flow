"use client";

import { useState } from "react";
import { useForm, Controller } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import * as z from "zod";
import { X, Mail, Loader2 } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { CustomSelect } from "@/components/ui/custom-select";
import { UserSearchSelect } from "@/components/ui/user-search-select";
import { usersApi } from "@/lib/api-endpoints";
import { UserRole } from "@/types";
import { getErrorMessage } from "@/lib/error-utils";
import { AnimatedModalShell } from "./AnimatedModalShell";

interface InviteUserModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
}

const inviteUserSchema = z.object({
  email: z.string().email("Invalid email address"),
  role: z.nativeEnum(UserRole),
});

type InviteUserFormValues = z.infer<typeof inviteUserSchema>;

export function InviteUserModal({
  isOpen,
  onClose,
  onSuccess,
}: InviteUserModalProps) {
  const [isSubmitting, setIsSubmitting] = useState(false);

  const {
    handleSubmit,
    control,
    reset,
    formState: { errors },
  } = useForm<InviteUserFormValues>({
    resolver: zodResolver(inviteUserSchema),
    defaultValues: {
      email: "",
      role: UserRole.MEMBER,
    },
  });

  const onSubmit = async (data: InviteUserFormValues) => {
    try {
      setIsSubmitting(true);
      await usersApi.inviteUser({
        email: data.email,
        role: data.role,
      });
      toast.success("User role updated successfully");
      reset();
      onSuccess();
      onClose();
    } catch (error) {
      console.error("Failed to invite user:", error);
      toast.error("Failed to invite user", {
        description: getErrorMessage(error),
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <AnimatedModalShell
      isOpen={isOpen}
      onClose={onClose}
      className="relative w-full max-w-lg rounded-2xl border border-border bg-popover shadow-2xl overflow-hidden"
    >
            {/* Header */}
            <div className="flex items-center justify-between p-6 border-b border-border">
              <div>
                <h2 className="text-xl font-semibold text-foreground">
                  Add Existing User
                </h2>
                <p className="text-sm text-muted-foreground mt-1">
                  Update role for an existing, registered user.
                </p>
              </div>
              <Button
                variant="ghost"
                size="icon"
                onClick={onClose}
                className="text-muted-foreground hover:text-foreground hover:bg-accent rounded-full"
              >
                <X className="h-5 w-5" />
              </Button>
            </div>

            {/* Form */}
            <div className="p-6">
              <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
                <div className="space-y-4">
                  {/* Email / User Search Field */}
                  <div className="space-y-2">
                    <label htmlFor="invite-user-email" className="text-sm font-medium text-foreground">
                      Find User
                    </label>
                    <div className="relative">
                      <Controller
                        name="email"
                        control={control}
                        render={({ field }) => (
                          <UserSearchSelect
                            value={field.value}
                            onChange={field.onChange}
                            id="invite-user-email"
                            name="email"
                            autoComplete="off"
                            placeholder="Search by name or email..."
                          />
                        )}
                      />
                    </div>
                    {errors.email && (
                      <p className="text-sm text-red-400">
                        {errors.email.message}
                      </p>
                    )}
                  </div>

                  {/* Role Selection */}
                  <div className="space-y-2">
                    <label htmlFor="invite-user-role" className="text-sm font-medium text-foreground">
                      Role
                    </label>
                    <Controller
                      name="role"
                      control={control}
                      render={({ field }) => (
                        <CustomSelect
                          value={field.value}
                          onChange={field.onChange}
                          id="invite-user-role"
                          name="role"
                          options={[
                            {
                              value: UserRole.ADMIN,
                              label: "Admin",
                              description: "Full access to everything",
                              color: "text-indigo-400",
                            },
                            {
                              value: UserRole.MANAGER,
                              label: "Manager",
                              description: "Manage projects & tasks",
                              color: "text-blue-400",
                            },
                            {
                              value: UserRole.MEMBER,
                              label: "Member",
                              description: "Can view & comment",
                              color: "text-emerald-400",
                            },
                            {
                              value: UserRole.VIEWER,
                              label: "Viewer",
                              description: "Read-only access",
                              color: "text-muted-foreground",
                            },
                          ]}
                          className="w-full h-auto"
                        />
                      )}
                    />
                    <p className="text-xs text-muted-foreground">
                      Assigning a new role will immediately update the user's
                      permissions.
                    </p>
                    {errors.role && (
                      <p className="text-sm text-red-400">
                        {errors.role.message}
                      </p>
                    )}
                  </div>
                </div>

                {/* Footer */}
                <div className="flex items-center justify-end gap-3 pt-2">
                  <Button
                    type="button"
                    variant="ghost"
                    onClick={onClose}
                    className="text-muted-foreground hover:text-foreground hover:bg-accent"
                    disabled={isSubmitting}
                  >
                    Cancel
                  </Button>
                  <Button
                    type="submit"
                    className="bg-primary hover:bg-primary/90 text-primary-foreground min-w-[120px]"
                    disabled={isSubmitting}
                  >
                    {isSubmitting ? (
                      <>
                        <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                        Sending...
                      </>
                    ) : (
                      <>
                        <Mail className="mr-2 h-4 w-4" />
                        Save Changes
                      </>
                    )}
                  </Button>
                </div>
              </form>
            </div>
    </AnimatedModalShell>
  );
}
