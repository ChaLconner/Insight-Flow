"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { DashboardLayout } from "@/components/layout/DashboardLayout";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { projectsApi } from "@/lib/api-endpoints";
import type { Project } from "@/types";
import { toast } from "sonner";
import { getErrorMessage } from "@/lib/error-utils";
import { ArrowLeft, Calendar, Users, BarChart2 } from "lucide-react";
import { Skeleton } from "@/components/ui/skeleton";
import { TaskList } from "@/components/tasks/TaskList";

export default function ProjectDetailsPage() {
    const params = useParams();
    const router = useRouter();
    const projectId = params.id as string;
    const [project, setProject] = useState<Project | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    const fetchProject = async (showLoading = true) => {
        try {
            if (showLoading) setLoading(true);
            const data = await projectsApi.getProject(projectId);
            setProject(data);
        } catch (err) {
            console.error("Failed to fetch project:", err);
            setError("Failed to load project details");
            if (!showLoading) { // Only show toast if not initial load to avoid double error UI
                toast.error("Failed to load project details", { description: getErrorMessage(err) });
            }
        } finally {
            if (showLoading) setLoading(false);
        }
    };

    useEffect(() => {
        if (projectId) {
            fetchProject(true);
        }
    }, [projectId]);

    if (loading) {
        return (
            <DashboardLayout>
                <div className="space-y-6">
                    <div className="flex items-center gap-4">
                        <Skeleton className="h-10 w-10 rounded-lg" />
                        <div className="space-y-2">
                            <Skeleton className="h-8 w-64" />
                            <Skeleton className="h-4 w-96" />
                        </div>
                    </div>
                    <div className="grid gap-6 md:grid-cols-3">
                        <Skeleton className="h-32" />
                        <Skeleton className="h-32" />
                        <Skeleton className="h-32" />
                    </div>
                </div>
            </DashboardLayout>
        );
    }

    if (error || !project) {
        return (
            <DashboardLayout>
                <div className="flex flex-col items-center justify-center h-[60vh] space-y-4">
                    <h2 className="text-2xl font-bold text-white">Project Not Found</h2>
                    <p className="text-zinc-400">{error || "The project you're looking for doesn't exist."}</p>
                    <Button onClick={() => router.push("/projects")}>
                        <ArrowLeft className="mr-2 h-4 w-4" />
                        Back to Projects
                    </Button>
                </div>
            </DashboardLayout>
        );
    }

    return (
        <DashboardLayout>
            <div className="space-y-8">
                {/* Header */}
                <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
                    <div className="space-y-2">
                        <div className="flex items-center gap-2">
                            <Button
                                variant="ghost"
                                size="sm"
                                className="text-zinc-400 hover:text-white hover:bg-white/5"
                                onClick={() => router.push("/projects")}
                            >
                                <ArrowLeft className="h-4 w-4 mr-2" />
                                Back to Projects
                            </Button>
                        </div>
                        <h1 className="text-3xl font-bold text-white">{project.name}</h1>
                        <p className="text-zinc-400 max-w-2xl">{project.description}</p>
                    </div>
                    <div className="flex gap-2">
                        <Button
                            variant="glass"
                            className="bg-transparent border-white/20 text-white hover:bg-white/10 hover:text-white hover:border-white/30 transition-all"
                            onClick={() => router.push(`/projects/${projectId}/settings`)}
                        >
                            Settings
                        </Button>
                    </div>
                </div>

                {/* Stats Grid */}
                <div className="grid gap-6 md:grid-cols-3">
                    <Card className="border-white/10 bg-white/5 backdrop-blur-sm">
                        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                            <CardTitle className="text-sm font-medium text-zinc-400">Tasks</CardTitle>
                            <Calendar className="h-4 w-4 text-zinc-400" />
                        </CardHeader>
                        <CardContent>
                            <div className="text-2xl font-bold text-white">{project.taskCount || 0}</div>
                            <p className="text-xs text-zinc-500">Active tasks</p>
                        </CardContent>
                    </Card>
                    <Card className="border-white/10 bg-white/5 backdrop-blur-sm">
                        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                            <CardTitle className="text-sm font-medium text-zinc-400">Members</CardTitle>
                            <Users className="h-4 w-4 text-zinc-400" />
                        </CardHeader>
                        <CardContent>
                            <div className="text-2xl font-bold text-white">{project.memberCount || 0}</div>
                            <p className="text-xs text-zinc-500">Team members</p>
                        </CardContent>
                    </Card>
                    <Card className="border-white/10 bg-white/5 backdrop-blur-sm">
                        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                            <CardTitle className="text-sm font-medium text-zinc-400">Progress</CardTitle>
                            <BarChart2 className="h-4 w-4 text-zinc-400" />
                        </CardHeader>
                        <CardContent>
                            <div className="text-2xl font-bold text-white">
                                {project.taskCount ? Math.round(((project.completedTasks || 0) / project.taskCount) * 100) : 0}%
                            </div>
                            <p className="text-xs text-zinc-500">Completion rate</p>
                        </CardContent>
                    </Card>
                </div>

                {/* Project Tasks */}
                <div className="space-y-4">
                    <TaskList
                        projectId={projectId}
                        title="Project Tasks"
                        description="Manage tasks for this project."
                        showProjectName={false}
                        onTaskChange={() => fetchProject(false)}
                    />
                </div>
            </div>
        </DashboardLayout>
    );
}
