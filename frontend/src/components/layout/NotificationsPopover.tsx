"use client";

import { useState, useEffect, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Bell, Trash2, Check } from "lucide-react";
import { formatDistanceToNow } from "date-fns";
import { Button } from "@/components/ui/button";
import { Notification } from "@/types";
import { cn } from "@/lib/utils";
import { useRouter } from "next/navigation";
import { useNotifications, useNotificationPolling } from "@/hooks/use-notifications";

export function NotificationsPopover() {
    const [isOpen, setIsOpen] = useState(false);
    const containerRef = useRef<HTMLDivElement>(null);
    const router = useRouter();

    // Use the hook for state and actions
    const {
        notifications,
        unreadCount,
        isLoading,
        markAsRead,
        markAllAsRead,
        removeNotification
    } = useNotifications();

    // Enable polling
    useNotificationPolling(30000); // Poll every 30 seconds

    // Close on click outside
    useEffect(() => {
        const handleClickOutside = (event: MouseEvent) => {
            if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
                setIsOpen(false);
            }
        };
        document.addEventListener("mousedown", handleClickOutside);
        return () => document.removeEventListener("mousedown", handleClickOutside);
    }, []);

    const handleMarkAsRead = async (id: string, e?: React.MouseEvent) => {
        if (e) { e.stopPropagation(); }
        await markAsRead(id);
    };

    const handleMarkAllAsRead = async () => {
        await markAllAsRead();
    };

    const handleDelete = async (id: string, e: React.MouseEvent) => {
        e.stopPropagation();
        await removeNotification(id);
    };

    const handleNotificationClick = async (notification: Notification) => {
        if (!notification.read) {
            await handleMarkAsRead(notification.id);
        }

        if (notification.actionUrl) {
            router.push(notification.actionUrl);
        }

        setIsOpen(false);
    };

    return (
        <div className="relative" ref={containerRef}>
            <Button
                variant="ghost"
                size="icon"
                className="relative h-10 w-10 rounded-full text-zinc-400 hover:bg-white/10 hover:text-white"
                onClick={() => setIsOpen(!isOpen)}
            >
                <Bell className="h-5 w-5" />
                {unreadCount > 0 && (
                    <span className="absolute right-2.5 top-2.5 h-2 w-2 rounded-full bg-indigo-500 ring-2 ring-black" />
                )}
            </Button>

            <AnimatePresence>
                {isOpen && (
                    <motion.div
                        initial={{ opacity: 0, y: 10, scale: 0.95 }}
                        animate={{ opacity: 1, y: 0, scale: 1 }}
                        exit={{ opacity: 0, y: 10, scale: 0.95 }}
                        transition={{ duration: 0.2 }}
                        className="absolute -right-16 sm:right-0 top-12 z-50 w-80 max-w-[calc(100vw-2rem)] sm:w-96 origin-top-right rounded-xl border border-white/10 bg-zinc-950/90 backdrop-blur-xl shadow-2xl ring-1 ring-black/5 flex flex-col"
                    >
                        <div className="flex items-center justify-between border-b border-white/10 p-4 shrink-0">
                            <h3 className="text-sm font-semibold text-white">Notifications</h3>
                            {unreadCount > 0 && (
                                <Button
                                    variant="ghost"
                                    size="sm"
                                    className="h-auto px-2 py-1 text-xs text-indigo-400 hover:text-indigo-300 hover:bg-indigo-500/10"
                                    onClick={handleMarkAllAsRead}
                                >
                                    Mark all as read
                                </Button>
                            )}
                        </div>

                        <div className="max-h-[60vh] sm:max-h-[400px] overflow-y-auto custom-scrollbar">
                            {isLoading && notifications.length === 0 ? (
                                <div className="flex flex-col items-center justify-center py-8 text-center">
                                    <div className="h-5 w-5 animate-spin rounded-full border-2 border-zinc-600 border-t-indigo-500 mb-2" />
                                    <p className="text-sm text-zinc-400">Loading...</p>
                                </div>
                            ) : notifications.length === 0 ? (
                                <div className="flex flex-col items-center justify-center py-8 text-center">
                                    <Bell className="h-8 w-8 text-zinc-600 mb-2" />
                                    <p className="text-sm text-zinc-400">No notifications yet</p>
                                </div>
                            ) : (
                                <div className="divide-y divide-white/5">
                                    {notifications.map((notification) => (
                                        <div
                                            key={notification.id}
                                            className={cn(
                                                "relative flex gap-3 p-4 transition-colors hover:bg-white/5 cursor-pointer group",
                                                !notification.read && "bg-indigo-500/5"
                                            )}
                                            onClick={() => handleNotificationClick(notification)}
                                        >
                                            <div className={cn(
                                                "mt-1 h-2 w-2 rounded-full shrink-0",
                                                !notification.read ? "bg-indigo-500" : "bg-transparent"
                                            )} />

                                            <div className="flex-1 space-y-1">
                                                <p className={cn("text-sm font-medium leading-none", !notification.read ? "text-white" : "text-zinc-400")}>
                                                    {notification.title}
                                                </p>
                                                <p className="text-xs text-zinc-500 line-clamp-2">
                                                    {notification.message}
                                                </p>
                                                <p className="text-[10px] text-zinc-600">
                                                    {formatDistanceToNow(new Date(notification.createdAt), { addSuffix: true })}
                                                </p>
                                            </div>

                                            <div className="flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                                                {!notification.read && (
                                                    <Button
                                                        variant="ghost"
                                                        size="icon"
                                                        className="h-6 w-6 text-zinc-500 hover:text-indigo-400 hover:bg-indigo-500/10"
                                                        onClick={(e) => handleMarkAsRead(notification.id, e)}
                                                        title="Mark as read"
                                                    >
                                                        <Check className="h-3 w-3" />
                                                    </Button>
                                                )}
                                                <Button
                                                    variant="ghost"
                                                    size="icon"
                                                    className="h-6 w-6 text-zinc-500 hover:text-red-400 hover:bg-red-500/10"
                                                    onClick={(e) => handleDelete(notification.id, e)}
                                                    title="Delete"
                                                >
                                                    <Trash2 className="h-3 w-3" />
                                                </Button>
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            )}
                        </div>
                    </motion.div>
                )}
            </AnimatePresence>
        </div>
    );
}
