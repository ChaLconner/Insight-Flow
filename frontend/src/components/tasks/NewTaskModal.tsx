"use client";

import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { X, AlertCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { tasksApi, projectsApi } from "@/lib/api-endpoints";
import type { Project, Task } from "@/types";
import { TaskPriority, TaskType } from "@/types";
import { useAuthStore } from "@/stores/auth-store";

interface NewTaskModalProps {
    isOpen: boolean;
    onClose: () => void;
    onTaskCreated: () => void;
    defaultProjectId?: string;
    task?: Task | null;
}

export function NewTaskModal({ isOpen, onClose, onTaskCreated, defaultProjectId, task }: NewTaskModalProps) {
    const [title, setTitle] = useState("");
    const [description, setDescription] = useState("");
    const [projectId, setProjectId] = useState(defaultProjectId || "");
    const [priority, setPriority] = useState<TaskPriority>(TaskPriority.MEDIUM);
    const [type, setType] = useState<TaskType>(TaskType.FEATURE);
    const [dueDate, setDueDate] = useState("");
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [projects, setProjects] = useState<Project[]>([]);



    useEffect(() => {
        if (isOpen) {
            if (task) {
                // Edit mode
                setTitle(task.title);
                setDescription(task.description || "");
                setProjectId(task.projectId);
                setPriority(task.priority);
                setType(task.type);
                setDueDate(task.dueDate ? new Date(task.dueDate).toISOString().split('T')[0] : "");
            } else {
                // Create mode - reset fields
                setTitle("");
                setDescription("");
                setProjectId(defaultProjectId || "");
                setPriority(TaskPriority.MEDIUM);
                setType(TaskType.FEATURE);
                setDueDate("");
            }
            setError(null);
        }
    }, [isOpen, task, defaultProjectId]);

    useEffect(() => {
        if (isOpen && !defaultProjectId && !task) {
            // Fetch projects if not provided and not editing
            const fetchProjects = async () => {
                try {
                    const response = await projectsApi.getProjects();
                    setProjects(Array.isArray(response) ? response : (response as any).data || []);
                } catch (err) {
                    console.error("Failed to fetch projects", err);
                }
            };
            fetchProjects();
        }
    }, [isOpen, defaultProjectId, task]);

    // Update projectId when defaultProjectId changes
    useEffect(() => {
        if (defaultProjectId && !task) {
            setProjectId(defaultProjectId);
        }
    }, [defaultProjectId, task]);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!title || !projectId) {
            setError("Title and Project are required");
            return;
        }

        setLoading(true);
        setError(null);

        try {
            if (task) {
                // Update existing task
                await tasksApi.updateTask(task.id, {
                    title,
                    description,
                    priority,
                    type,
                    dueDate: dueDate ? new Date(dueDate).toISOString() : undefined,
                });
            } else {
                // Create new task
                await tasksApi.createTask(projectId, {
                    title,
                    description,
                    projectId,
                    priority,
                    type,
                    dueDate: dueDate ? new Date(dueDate).toISOString() : undefined,
                });
            }
            onTaskCreated();
            onClose();
            // Reset form only if creating a new task
            if (!task) {
                setTitle("");
                setDescription("");
                if (!defaultProjectId) { setProjectId(""); }
                setPriority(TaskPriority.MEDIUM);
                setType(TaskType.FEATURE);
                setDueDate("");
            }
        } catch (err) {
            console.error("Failed to save task", err);
            setError("Failed to save task. Please try again.");
        } finally {
            setLoading(false);
        }
    };

    return (
        <AnimatePresence>
            {isOpen && (
                <>
                    <motion.div
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        onClick={onClose}
                        className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50"
                    />
                    <motion.div
                        initial={{ opacity: 0, scale: 0.95, y: 20 }}
                        animate={{ opacity: 1, scale: 1, y: 0 }}
                        exit={{ opacity: 0, scale: 0.95, y: 20 }}
                        className="fixed left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 w-full max-w-lg bg-[#0A0A0A] border border-white/10 rounded-xl shadow-2xl z-50 overflow-hidden"
                    >
                        <div className="p-6 space-y-6">
                            <div className="flex items-center justify-between">
                                <h2 className="text-xl font-semibold text-white">{task ? "Edit Task" : "New Task"}</h2>
                                <Button variant="ghost" size="icon" onClick={onClose} className="text-zinc-400 hover:text-white">
                                    <X className="h-5 w-5" />
                                </Button>
                            </div>

                            {error && (
                                <div className="bg-red-500/10 border border-red-500/20 rounded-lg p-3 flex items-center gap-2 text-red-400 text-sm">
                                    <AlertCircle className="h-4 w-4" />
                                    {error}
                                </div>
                            )}

                            <form onSubmit={handleSubmit} className="space-y-4">
                                <div className="space-y-2">
                                    <label className="text-sm font-medium text-zinc-400">Title</label>
                                    <Input
                                        value={title}
                                        onChange={(e) => setTitle(e.target.value)}
                                        placeholder="What needs to be done?"
                                        className="bg-white/5 border-white/10 text-white placeholder:text-zinc-500"
                                        autoFocus
                                    />
                                </div>

                                <div className="space-y-2">
                                    <label className="text-sm font-medium text-zinc-400">Description</label>
                                    <textarea
                                        value={description}
                                        onChange={(e) => setDescription(e.target.value)}
                                        placeholder="Add more details..."
                                        className="w-full min-h-[100px] rounded-md border border-white/10 bg-white/5 px-3 py-2 text-sm text-white placeholder:text-zinc-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/50"
                                    />
                                </div>

                                <div className="grid grid-cols-2 gap-4">
                                    {!defaultProjectId && !task && (
                                        <div className="space-y-2 col-span-2">
                                            <label className="text-sm font-medium text-zinc-400">Project</label>
                                            <select
                                                value={projectId}
                                                onChange={(e) => setProjectId(e.target.value)}
                                                className="w-full rounded-md border border-white/10 bg-white/5 px-3 py-2 text-sm text-white focus:outline-none focus:ring-2 focus:ring-indigo-500/50"
                                            >
                                                <option value="" disabled>Select a project</option>
                                                {projects.map((p) => (
                                                    <option key={p.id} value={p.id} className="bg-zinc-900">
                                                        {p.name}
                                                    </option>
                                                ))}
                                            </select>
                                        </div>
                                    )}

                                    <div className="space-y-2">
                                        <label className="text-sm font-medium text-zinc-400">Priority</label>
                                        <select
                                            value={priority}
                                            onChange={(e) => setPriority(e.target.value as TaskPriority)}
                                            className="w-full rounded-md border border-white/10 bg-white/5 px-3 py-2 text-sm text-white focus:outline-none focus:ring-2 focus:ring-indigo-500/50"
                                        >
                                            {Object.values(TaskPriority).map((p) => (
                                                <option key={p} value={p} className="bg-zinc-900">
                                                    {p.charAt(0).toUpperCase() + p.slice(1)}
                                                </option>
                                            ))}
                                        </select>
                                    </div>

                                    <div className="space-y-2">
                                        <label className="text-sm font-medium text-zinc-400">Type</label>
                                        <select
                                            value={type}
                                            onChange={(e) => setType(e.target.value as TaskType)}
                                            className="w-full rounded-md border border-white/10 bg-white/5 px-3 py-2 text-sm text-white focus:outline-none focus:ring-2 focus:ring-indigo-500/50"
                                        >
                                            {Object.values(TaskType).map((t) => (
                                                <option key={t} value={t} className="bg-zinc-900">
                                                    {t.charAt(0).toUpperCase() + t.slice(1)}
                                                </option>
                                            ))}
                                        </select>
                                    </div>

                                    <div className="space-y-2">
                                        <label className="text-sm font-medium text-zinc-400">Due Date</label>
                                        <Input
                                            type="date"
                                            value={dueDate}
                                            onChange={(e) => setDueDate(e.target.value)}
                                            className="bg-white/5 border-white/10 text-white"
                                        />
                                    </div>
                                </div>

                                <div className="flex justify-end gap-3 pt-4">
                                    <Button type="button" variant="ghost" onClick={onClose} className="text-zinc-400 hover:text-white">
                                        Cancel
                                    </Button>
                                    <Button
                                        type="submit"
                                        disabled={loading}
                                        className="bg-indigo-600 hover:bg-indigo-500 text-white"
                                    >
                                        {loading ? (task ? "Saving..." : "Creating...") : (task ? "Save Changes" : "Create Task")}
                                    </Button>
                                </div>
                            </form>
                        </div>
                    </motion.div>
                </>
            )}
        </AnimatePresence>
    );
}
