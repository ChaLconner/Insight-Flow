"use client";

import { useState } from "react";
import { useForm, Controller } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import * as z from "zod";
import { motion, AnimatePresence } from "framer-motion";
import { X, Mail, Loader2 } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { CustomSelect } from "@/components/ui/custom-select";
import { UserSearchSelect } from "@/components/ui/user-search-select";
import { usersApi } from "@/lib/api-endpoints";
import { UserRole } from "@/types";
import { getErrorMessage } from "@/lib/error-utils";

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
    <AnimatePresence>
      {isOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
            className="absolute inset-0 bg-black/60 backdrop-blur-sm"
          />
          <motion.div
            initial={{ opacity: 0, scale: 0.95, y: 20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: 20 }}
            className="relative w-full max-w-lg rounded-2xl border border-white/10 bg-[#18181b] shadow-2xl overflow-hidden"
          >
            {/* Header */}
            <div className="flex items-center justify-between p-6 border-b border-white/10">
              <div>
                <h2 className="text-xl font-semibold text-white">
                  Add Existing User
                </h2>
                <p className="text-sm text-zinc-400 mt-1">
                  Update role for an existing, registered user.
                </p>
              </div>
              <Button
                variant="ghost"
                size="icon"
                onClick={onClose}
                className="text-zinc-400 hover:text-white hover:bg-white/10 rounded-full"
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
                    <label className="text-sm font-medium text-zinc-300">
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
                    <label className="text-sm font-medium text-zinc-300">
                      Role
                    </label>
                    <Controller
                      name="role"
                      control={control}
                      render={({ field }) => (
                        <CustomSelect
                          value={field.value}
                          onChange={field.onChange}
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
                              color: "text-zinc-400",
                            },
                          ]}
                          className="w-full h-auto"
                        />
                      )}
                    />
                    <p className="text-xs text-zinc-500">
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
                    className="text-zinc-400 hover:text-white hover:bg-white/10"
                    disabled={isSubmitting}
                  >
                    Cancel
                  </Button>
                  <Button
                    type="submit"
                    className="bg-indigo-600 hover:bg-indigo-500 text-white min-w-[120px]"
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
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  );
}
