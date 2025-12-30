"use client";

import { useState, useEffect, useRef, useMemo } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Bell, Trash2, Check } from "lucide-react";
import { formatDistanceToNow, isToday, isYesterday } from "date-fns";
import { Button } from "@/components/ui/button";
import type { Notification } from "@/types";
import { cn } from "@/lib/utils";
import { toast } from "sonner";
import { useRouter } from "next/navigation";
import {
  useNotifications,
  useNotificationPolling,
} from "@/hooks/use-notifications";

export function NotificationsPopover() {
  const [isOpen, setIsOpen] = useState(false);
  const [activeTab, setActiveTab] = useState<"all" | "unread" | "mentions">("all");
  const containerRef = useRef<HTMLDivElement>(null);
  const router = useRouter();

  const {
    notifications,
    unreadCount,
    isLoading,
    markAsRead,
    markAllAsRead,
    removeNotification,
  } = useNotifications();

  useNotificationPolling(60000);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (
        containerRef.current &&
        !containerRef.current.contains(event.target as Node)
      ) {
        setIsOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const handleMarkAsRead = async (id: string, e?: React.MouseEvent) => {
    if (e) {
      e.stopPropagation();
    }
    await markAsRead(id);
  };

  const handleMarkAllAsRead = async () => {
    await markAllAsRead();
  };

  const handleDelete = async (notification: Notification, e: React.MouseEvent) => {
    e.stopPropagation();
    await removeNotification(notification.id);
    toast.success("Notification deleted");
  };

  // Get dot color based on notification type
  const getNotificationDotColor = (type: string): string => {
    switch (type) {
      case "task_assigned":
        return "bg-blue-500";
      case "project_invitation":
      case "project_member_joined":
        return "bg-emerald-500";
      case "task_due_soon":
        return "bg-amber-500";
      case "task_overdue":
        return "bg-red-500";
      case "task_completed":
      case "task_updated":
        return "bg-green-500";
      case "mention":
        return "bg-purple-500";
      case "project_member_left":
        return "bg-orange-500";
      default:
        return "bg-indigo-500";
    }
  };

  const getNotificationUrl = (notification: Notification): string | null => {
    const data = notification.data as Record<string, string | number | boolean | null> | undefined;

    if (!data) {
      return null;
    }

    const projectId = data.project_id as string;
    const taskId = data.task_id as string;

    if (taskId && projectId) {
      return `/projects/${projectId}?task=${taskId}`;
    }

    if (projectId) {
      return `/projects/${projectId}`;
    }

    return null;
  };

  const handleNotificationClick = async (notification: Notification) => {
    if (!notification.read) {
      await handleMarkAsRead(notification.id);
    }

    const url = notification.actionUrl ?? getNotificationUrl(notification);

    if (url) {
      router.push(url);
    }

    setIsOpen(false);
  };

  const groupedNotifications = useMemo(() => {
    const filtered = notifications.filter((n) => {
      if (activeTab === "unread") {
        return !n.read;
      }
      if (activeTab === "mentions") {
        return n.type === "mention";
      }
      return true;
    });

    const today: Notification[] = [];
    const yesterday: Notification[] = [];
    const earlier: Notification[] = [];

    filtered.forEach((n) => {
      const date = new Date(n.createdAt);
      if (isToday(date)) {
        today.push(n);
      } else if (isYesterday(date)) {
        yesterday.push(n);
      } else {
        earlier.push(n);
      }
    });

    const groups = [];
    if (today.length > 0) {
      groups.push({ label: "Today", items: today });
    }
    if (yesterday.length > 0) {
      groups.push({ label: "Yesterday", items: yesterday });
    }
    if (earlier.length > 0) {
      groups.push({ label: "Earlier", items: earlier });
    }

    return groups;
  }, [notifications, activeTab]);

  return (
    <div className="relative" ref={containerRef}>
      <Button
        variant="ghost"
        size="icon"
        className="relative h-10 w-10 rounded-full text-muted-foreground hover:bg-transparent hover:text-foreground transition-none"
        onClick={() => setIsOpen(!isOpen)}
        whileHover={{ scale: 1 }}
      >
        <Bell className="h-5 w-5" />
        {unreadCount > 0 && (
          <span className="absolute right-1 top-1 flex min-w-[18px] h-[18px] items-center justify-center rounded-full bg-red-500 px-1 text-[10px] font-bold text-white transition-none">
            {unreadCount > 99 ? "99+" : unreadCount}
          </span>
        )}
      </Button>

      <AnimatePresence mode="wait">
        {isOpen && (
          <motion.div
            initial={{ opacity: 0, y: 8, scale: 0.98 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 8, scale: 0.98 }}
            transition={{ duration: 0.15, ease: "easeOut" }}
            className="absolute -right-16 sm:right-0 top-12 z-50 w-80 sm:w-96 origin-top-right rounded-xl border border-border bg-popover/95 backdrop-blur-xl shadow-2xl flex flex-col max-h-[600px]"
          >
            {/* Header */}
            <div className="flex items-center justify-between border-b border-border px-4 py-3 shrink-0">
              <h3 className="text-sm font-semibold text-foreground">
                Notifications
                {unreadCount > 0 && (
                  <span className="ml-2 text-xs font-normal text-muted-foreground">
                    ({unreadCount} unread)
                  </span>
                )}
              </h3>
              {unreadCount > 0 && (
                <button
                  className="text-xs text-primary hover:text-primary/80 transition-colors"
                  onClick={handleMarkAllAsRead}
                >
                  Mark all read
                </button>
              )}
            </div>

            {/* Tabs */}
            <div className="flex items-center px-4 pt-3 pb-2 gap-4 border-b border-border/50 shrink-0">
              {(["all", "unread", "mentions"] as const).map((tab) => (
                <button
                  key={tab}
                  onClick={() => setActiveTab(tab)}
                  className={cn(
                    "text-xs font-medium pb-2 transition-colors relative",
                    activeTab === tab
                      ? "text-foreground"
                      : "text-muted-foreground hover:text-foreground/80"
                  )}
                >
                  {tab.charAt(0).toUpperCase() + tab.slice(1)}
                  {activeTab === tab && (
                    <motion.div
                      layoutId="activeTab"
                      className="absolute bottom-0 left-0 right-0 h-0.5 bg-primary rounded-full"
                    />
                  )}
                </button>
              ))}
            </div>

            {/* Content */}
            <div className="overflow-y-auto flex-1 custom-scrollbar">
              {isLoading && notifications.length === 0 ? (
                <div className="flex items-center justify-center py-8">
                  <div className="h-5 w-5 animate-spin rounded-full border-2 border-muted border-t-primary" />
                </div>
              ) : groupedNotifications.length === 0 ? (
                <div className="py-12 text-center">
                  <Bell className="h-8 w-8 text-muted-foreground/50 mx-auto mb-3" />
                  <p className="text-sm text-muted-foreground">No notifications found</p>
                </div>
              ) : (
                <div className="pb-2">
                  {groupedNotifications.map((group) => (
                    <div key={group.label}>
                      <div className="sticky top-0 z-10 bg-popover/95 backdrop-blur-sm px-4 py-2 text-[11px] font-semibold text-muted-foreground uppercase tracking-wider border-y border-border/50">
                        {group.label}
                      </div>
                      <div>
                        {group.items.map((notification) => (
                          <div
                            key={notification.id}
                            className={cn(
                              "group flex items-start gap-3 px-4 py-3 cursor-pointer transition-colors hover:bg-accent border-b border-border/50 last:border-0",
                              !notification.read && "bg-primary/5"
                            )}
                            onClick={() => handleNotificationClick(notification)}
                          >
                            {/* Unread indicator */}
                            <div className="pt-1.5 shrink-0">
                              <div
                                className={cn(
                                  "h-2 w-2 rounded-full",
                                  !notification.read ? getNotificationDotColor(notification.type) : "bg-transparent"
                                )}
                              />
                            </div>

                            {/* Content */}
                            <div className="flex-1 min-w-0">
                              <p
                                className={cn(
                                  "text-sm leading-snug",
                                  !notification.read
                                    ? "text-foreground font-medium"
                                    : "text-muted-foreground"
                                )}
                              >
                                {notification.title}
                              </p>
                              <p className="text-xs text-muted-foreground mt-0.5 line-clamp-2">
                                {notification.message}
                              </p>
                              <p className="text-[10px] text-muted-foreground/70 mt-1.5 flex items-center gap-1.5">
                                <span>
                                  {formatDistanceToNow(new Date(notification.createdAt), {
                                    addSuffix: true,
                                  })}
                                </span>
                              </p>
                            </div>

                            {/* Actions */}
                            <div className="flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity self-center">
                              {!notification.read && (
                                <button
                                  className="p-1.5 rounded-md text-muted-foreground hover:text-primary hover:bg-primary/10 transition-all"
                                  onClick={(e) => handleMarkAsRead(notification.id, e)}
                                  title="Mark as read"
                                >
                                  <Check className="h-3.5 w-3.5" />
                                </button>
                              )}
                              <button
                                className="p-1.5 rounded-md text-muted-foreground hover:text-destructive hover:bg-destructive/10 transition-all"
                                onClick={(e) => handleDelete(notification, e)}
                                title="Delete"
                              >
                                <Trash2 className="h-3.5 w-3.5" />
                              </button>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  ))}

                  {/* Load More Trigger */}
                  <div className="p-2 border-t border-border/50">
                     <Button
                        variant="ghost"
                        className="w-full text-xs text-muted-foreground hover:text-foreground h-8"
                        onClick={() => {
                          /* TODO: Implement Load More logic */
                        }}
                     >
                        Load Previous Notifications
                     </Button>
                  </div>
                </div>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
