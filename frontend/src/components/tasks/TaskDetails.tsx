import Link from "next/link";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { ArrowLeft, Calendar, User as UserIcon, Clock } from "lucide-react";
import { format } from "date-fns";
import type { Task } from "@/types";

interface TaskDetailsProps {
    task: Task;
    backLink: string;
    backLabel: string;
}

function getStatusColor(status: string) {
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
}

export function TaskDetails({ task, backLink, backLabel }: TaskDetailsProps) {
    return (
        <div className="space-y-8 max-w-4xl mx-auto">
            {/* Header */}
            <div className="space-y-4">
                <Link href={backLink} passHref>
                    <Button
                        variant="ghost"
                        size="sm"
                        className="p-0 h-auto hover:bg-transparent text-zinc-400 hover:text-white"
                    >
                        <ArrowLeft className="h-4 w-4 mr-1" />
                        {backLabel}
                    </Button>
                </Link>

                <div className="flex flex-col md:flex-row md:items-start md:justify-between gap-4">
                    <div className="space-y-2">
                        <h1 className="text-3xl font-bold text-white">{task.title}</h1>
                        <div className="flex items-center gap-3">
                            <Badge className={getStatusColor(task.status)}>
                                {task.status.replace('_', ' ')}
                            </Badge>
                            <span className="text-zinc-500 text-sm">
                                Created {task.createdAt ? format(new Date(task.createdAt), 'MMM d, yyyy') : 'Unknown'}
                            </span>
                        </div>
                    </div>
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
                                {task.description ?? "No description provided."}
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
                                <div className="h-8 w-8 rounded-lg bg-primary/10 flex items-center justify-center">
                                    <UserIcon className="h-4 w-4 text-primary" />
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
    );
}
