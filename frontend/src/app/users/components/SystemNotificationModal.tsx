"use client";

import { useMemo, useState } from "react";
import { BellRing, Loader2, Megaphone, Send, X } from "lucide-react";
import { toast } from "sonner";

import type { User } from "@/types";
import { usersApi } from "@/lib/api-endpoints";
import { getErrorMessage } from "@/lib/error-utils";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { AnimatedModalShell } from "@/components/modals/AnimatedModalShell";
import { cn } from "@/lib/utils";

interface SystemNotificationModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
  users: User[];
}

export function SystemNotificationModal({
  isOpen,
  onClose,
  onSuccess,
  users,
}: SystemNotificationModalProps) {
  const [title, setTitle] = useState("");
  const [message, setMessage] = useState("");
  const [selectedUserIds, setSelectedUserIds] = useState<string[]>([]);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const selectedCount = selectedUserIds.length;
  const canSubmit = title.trim().length > 0 && message.trim().length > 0 && selectedCount > 0;

  const selectableUsers = useMemo(
    () =>
      users.filter((user) => user.isActive).map((user) => {
        const fullName = `${user.firstName ?? ""} ${user.lastName ?? ""}`.trim();

        return {
          ...user,
          displayName:
            fullName.length > 0 ? fullName : user.name ?? user.username ?? user.email,
        };
      }),
    [users],
  );

  const toggleUser = (userId: string) => {
    setSelectedUserIds((current) =>
      current.includes(userId)
        ? current.filter((id) => id !== userId)
        : [...current, userId],
    );
  };

  const resetForm = () => {
    setTitle("");
    setMessage("");
    setSelectedUserIds([]);
    setIsSubmitting(false);
  };

  const handleClose = () => {
    resetForm();
    onClose();
  };

  const handleSubmit = async () => {
    if (!canSubmit) {
      return;
    }

    try {
      setIsSubmitting(true);
      const result = await usersApi.sendSystemNotification({
        title: title.trim(),
        message: message.trim(),
        targetUserIds: selectedUserIds,
        data: { source: "users-page" },
      });
      toast.success(`Sent to ${result.count} user${result.count === 1 ? "" : "s"}`);
      onSuccess();
      handleClose();
    } catch (error) {
      toast.error("Failed to send system notification", {
        description: getErrorMessage(error),
      });
      setIsSubmitting(false);
    }
  };

  return (
    <AnimatedModalShell
      isOpen={isOpen}
      onClose={handleClose}
      className="relative w-full max-w-2xl rounded-2xl border border-border bg-popover shadow-2xl overflow-hidden"
    >
      <div className="flex items-center justify-between p-6 border-b border-border">
        <div>
          <h2 className="text-xl font-semibold text-foreground flex items-center gap-2">
            <Megaphone className="h-5 w-5 text-amber-500" />
            Send System Notification
          </h2>
          <p className="text-sm text-muted-foreground mt-1">
            Send an in-app system alert to selected active users.
          </p>
        </div>
        <Button
          variant="ghost"
          size="icon"
          onClick={handleClose}
          className="text-muted-foreground hover:text-foreground hover:bg-accent rounded-full"
        >
          <X className="h-5 w-5" />
        </Button>
      </div>

      <div className="p-6 space-y-6">
        <div className="space-y-2">
          <label htmlFor="system-notification-title" className="text-sm font-medium text-foreground">
            Title
          </label>
          <Input
            id="system-notification-title"
            value={title}
            onChange={(event) => setTitle(event.target.value)}
            placeholder="Maintenance notice"
            maxLength={200}
          />
        </div>

        <div className="space-y-2">
          <label htmlFor="system-notification-message" className="text-sm font-medium text-foreground">
            Message
          </label>
          <Textarea
            id="system-notification-message"
            value={message}
            onChange={(event) => setMessage(event.target.value)}
            placeholder="Planned maintenance starts at 10:00 PM."
            className="min-h-[120px] bg-background border-border"
            maxLength={2000}
          />
        </div>

        <div className="space-y-3">
          <div className="flex items-center justify-between gap-3">
            <div>
              <p className="text-sm font-medium text-foreground">Recipients</p>
              <p className="text-xs text-muted-foreground">
                Pick from the active users currently shown in this list.
              </p>
            </div>
            <div className="text-xs text-muted-foreground flex items-center gap-1.5">
              <BellRing className="h-3.5 w-3.5 text-amber-500" />
              {selectedCount} selected
            </div>
          </div>

          <div className="max-h-72 overflow-y-auto rounded-xl border border-border bg-background/60 p-2">
            {selectableUsers.length === 0 ? (
              <div className="px-3 py-6 text-sm text-center text-muted-foreground">
                No active users available in the current list.
              </div>
            ) : (
              <div className="space-y-2">
                {selectableUsers.map((user) => {
                  const isSelected = selectedUserIds.includes(user.id);
                  return (
                    <button
                      key={user.id}
                      type="button"
                      onClick={() => toggleUser(user.id)}
                      className={cn(
                        "w-full rounded-lg border px-3 py-2 text-left transition-colors",
                        isSelected
                          ? "border-amber-500/40 bg-amber-500/10"
                          : "border-border hover:bg-accent/60",
                      )}
                    >
                      <div className="flex items-center justify-between gap-3">
                        <div className="min-w-0">
                          <p className="truncate text-sm font-medium text-foreground">
                            {user.displayName}
                          </p>
                          <p className="truncate text-xs text-muted-foreground">
                            {user.email}
                          </p>
                        </div>
                        <span
                          className={cn(
                            "text-[11px] font-semibold uppercase tracking-wide",
                            isSelected ? "text-amber-400" : "text-muted-foreground",
                          )}
                        >
                          {isSelected ? "Selected" : "Select"}
                        </span>
                      </div>
                    </button>
                  );
                })}
              </div>
            )}
          </div>
        </div>

        <div className="flex items-center justify-end gap-3 pt-2">
          <Button
            type="button"
            variant="ghost"
            onClick={handleClose}
            className="text-muted-foreground hover:text-foreground hover:bg-accent"
            disabled={isSubmitting}
          >
            Cancel
          </Button>
          <Button
            type="button"
            onClick={handleSubmit}
            className="bg-amber-600 hover:bg-amber-500 text-white min-w-[140px]"
            disabled={!canSubmit || isSubmitting}
          >
            {isSubmitting ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Sending...
              </>
            ) : (
              <>
                <Send className="mr-2 h-4 w-4" />
                Send Alert
              </>
            )}
          </Button>
        </div>
      </div>
    </AnimatedModalShell>
  );
}
