"use client";

import { useRef } from "react";
import { useRouter } from "next/navigation";
import { DashboardLayout } from "@/components/layout/DashboardLayout";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { type Project, TaskStatus } from "@/types";
import { ArrowLeft, Calendar, Users, BarChart2, Plus } from "lucide-react";
import { TaskList, type TaskListRef } from "@/components/tasks/TaskList";

interface ProjectDetailsClientProps {
    project: Project;
}

export function ProjectDetailsClient({ project: initialProject }: ProjectDetailsClientProps) {
    const router = useRouter();
    const projectId = initialProject.id;
    const taskListRef = useRef<TaskListRef>(null);

    const handleBack = () => {
        router.push("/projects");
    };

    return (
        <div className="space-y-8">
            {/* Header */}
            <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
                <div className="space-y-2">
                    <div className="flex items-center gap-2">
                        <Button
                            variant="ghost"
                            size="sm"
                            className="text-zinc-400 hover:text-white hover:bg-white/5"
                            onClick={handleBack}
                        >
                            <ArrowLeft className="h-4 w-4 mr-2" />
                            Back to Projects
                        </Button>
                    </div>
                    <h1 className="text-3xl font-bold text-white">{initialProject.name}</h1>
                    <p className="text-zinc-400 max-w-2xl">{initialProject.description}</p>
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
                        <div className="text-2xl font-bold text-white">{initialProject.taskCount || 0}</div>
                        <p className="text-xs text-zinc-500">Active tasks</p>
                    </CardContent>
                </Card>
                <Card className="border-white/10 bg-white/5 backdrop-blur-sm">
                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                        <CardTitle className="text-sm font-medium text-zinc-400">Members</CardTitle>
                        <Users className="h-4 w-4 text-zinc-400" />
                    </CardHeader>
                    <CardContent>
                        <div className="text-2xl font-bold text-white">{initialProject.memberCount || 0}</div>
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
                            {initialProject.taskCount ? Math.round(((initialProject.completedTasks || 0) / initialProject.taskCount) * 100) : 0}%
                        </div>
                        <p className="text-xs text-zinc-500">Completion rate</p>
                    </CardContent>
                </Card>
            </div>

            {/* Project Tasks */}
            <div className="space-y-4">
                <div className="flex items-center justify-between">
                    <h2 className="text-xl font-semibold text-white">Project Tasks</h2>
                    <Button
                        onClick={() => taskListRef.current?.openNewTaskModal()}
                        className="bg-indigo-600 hover:bg-indigo-700 text-white"
                        size="sm"
                    >
                        <Plus className="h-4 w-4 mr-2" />
                        Create Task
                    </Button>
                </div>

                <TaskList
                    ref={taskListRef}
                    projectId={projectId}
                    title="Tasks"
                    description="Manage tasks for this project."
                    hideHeader={true}
                    showProjectName={false}
                    onTaskChange={() => {
                        // Trigger a router.refresh() to update stats
                        router.refresh();
                    }}
                />
            </div>
        </div>
    );
}
