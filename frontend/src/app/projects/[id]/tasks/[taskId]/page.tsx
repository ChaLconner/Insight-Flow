"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { DashboardLayout } from "@/components/layout/DashboardLayout";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { tasksApi } from "@/lib/api-endpoints";
import type { Task } from "@/types";
import { ArrowLeft, Calendar, User as UserIcon, Clock, CheckCircle2, AlertCircle } from "lucide-react";
import { Skeleton } from "@/components/ui/skeleton";
import { format } from "date-fns";

export default function TaskDetailsPage() {
    const params = useParams();
    const router = useRouter();
    const projectId = params.id as string;
    const taskId = params.taskId as string;

    const [task, setTask] = useState<Task | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        const fetchTask = async () => {
            try {
                setLoading(true);
                const data = await tasksApi.getTask(taskId);
                setTask(data);
            } catch (err) {
                console.error("Failed to fetch task:", err);
                setError("Failed to load task details");
            } finally {
                setLoading(false);
            }
        };

        if (taskId) {
            fetchTask();
        }
    }, [taskId]);

    const getStatusColor = (status: string) => {
        switch (status.toLowerCase()) {
            case 'done':
            case 'completed':
                return "bg-emerald-500/20 text-emerald-400 hover:bg-emerald-500/30";
            case 'in_progress':
                return "bg-blue-500/20 text-blue-400 hover:bg-blue-500/30";
            case 'todo':
                return "bg-zinc-500/20 text-zinc-400 hover:bg-zinc-500/30";
            default:
                return "bg-zinc-500/20 text-zinc-400";
        }
    };

    if (loading) {
        return (
            <DashboardLayout>
                <div className="space-y-6 max-w-4xl mx-auto">
                    <div className="flex items-center gap-4">
                        <Skeleton className="h-10 w-10 rounded-lg" />
                        <div className="space-y-2">
                            <Skeleton className="h-8 w-64" />
                            <Skeleton className="h-4 w-32" />
                        </div>
                    </div>
                    <Card className="border-white/10 bg-white/5">
                        <CardContent className="p-6 space-y-6">
                            <Skeleton className="h-4 w-full" />
                            <Skeleton className="h-4 w-full" />
                            <Skeleton className="h-4 w-2/3" />
                        </CardContent>
                    </Card>
                </div>
            </DashboardLayout>
        );
    }

    if (error || !task) {
        return (
            <DashboardLayout>
                <div className="flex flex-col items-center justify-center h-[60vh] space-y-4">
                    <div className="h-12 w-12 rounded-full bg-red-500/10 flex items-center justify-center">
                        <AlertCircle className="h-6 w-6 text-red-400" />
                    </div>
                    <h2 className="text-2xl font-bold text-white">Task Not Found</h2>
                    <p className="text-zinc-400">{error || "The task you're looking for doesn't exist."}</p>
                    <Button onClick={() => router.push(`/projects/${projectId}`)}>
                        <ArrowLeft className="mr-2 h-4 w-4" />
                        Back to Project
                    </Button>
                </div>
            </DashboardLayout>
        );
    }

    return (
        <DashboardLayout>
            <div className="space-y-8 max-w-4xl mx-auto">
                {/* Header */}
                <div className="space-y-4">
                    <Button
                        variant="ghost"
                        size="sm"
                        className="p-0 h-auto hover:bg-transparent text-zinc-400 hover:text-white"
                        onClick={() => router.push(`/projects/${projectId}`)}
                    >
                        <ArrowLeft className="h-4 w-4 mr-1" />
                        Back to Project
                    </Button>

                    <div className="flex flex-col md:flex-row md:items-start md:justify-between gap-4">
                        <div className="space-y-2">
                            <h1 className="text-3xl font-bold text-white">{task.title}</h1>
                            <div className="flex items-center gap-3">
                                <Badge className={getStatusColor(task.status)}>
                                    {task.status.replace('_', ' ')}
                                </Badge>
                                <span className="text-zinc-500 text-sm">
                                    Created {format(new Date(task.createdAt || new Date()), 'MMM d, yyyy')}
                                </span>
                            </div>
                        </div>
                        {/* Actions could go here */}
                    </div>
                </div>

                <div className="grid gap-6 md:grid-cols-3">
                    {/* Main Content */}
                    <div className="md:col-span-2 space-y-6">
                        <Card className="border-white/10 bg-white/5 backdrop-blur-sm">
                            <CardHeader>
                                <CardTitle className="text-lg font-medium text-white">Description</CardTitle>
                            </CardHeader>
                            <CardContent>
                                <p className="text-zinc-300 leading-relaxed whitespace-pre-wrap">
                                    {task.description || "No description provided."}
                                </p>
                            </CardContent>
                        </Card>
                    </div>

                    {/* Sidebar */}
                    <div className="space-y-6">
                        <Card className="border-white/10 bg-white/5 backdrop-blur-sm">
                            <CardHeader>
                                <CardTitle className="text-sm font-medium text-zinc-400 uppercase tracking-wider">Details</CardTitle>
                            </CardHeader>
                            <CardContent className="space-y-4">
                                <div className="flex items-center gap-3">
                                    <div className="h-8 w-8 rounded-lg bg-indigo-500/10 flex items-center justify-center">
                                        <UserIcon className="h-4 w-4 text-indigo-400" />
                                    </div>
                                    <div>
                                        <p className="text-xs text-zinc-500">Assignee</p>
                                        <p className="text-sm font-medium text-white">
                                            {task.assignee ? `${task.assignee.firstName} ${task.assignee.lastName}` : 'Unassigned'}
                                        </p>
                                    </div>
                                </div>

                                <div className="flex items-center gap-3">
                                    <div className="h-8 w-8 rounded-lg bg-amber-500/10 flex items-center justify-center">
                                        <Calendar className="h-4 w-4 text-amber-400" />
                                    </div>
                                    <div>
                                        <p className="text-xs text-zinc-500">Due Date</p>
                                        <p className="text-sm font-medium text-white">
                                            {task.dueDate ? format(new Date(task.dueDate), 'MMM d, yyyy') : 'No due date'}
                                        </p>
                                    </div>
                                </div>

                                <div className="flex items-center gap-3">
                                    <div className="h-8 w-8 rounded-lg bg-emerald-500/10 flex items-center justify-center">
                                        <Clock className="h-4 w-4 text-emerald-400" />
                                    </div>
                                    <div>
                                        <p className="text-xs text-zinc-500">Last Updated</p>
                                        <p className="text-sm font-medium text-white">
                                            {task.updatedAt ? format(new Date(task.updatedAt), 'MMM d, yyyy') : 'Never'}
                                        </p>
                                    </div>
                                </div>
                            </CardContent>
                        </Card>
                    </div>
                </div>
            </div>
        </DashboardLayout>
    );
}
