"use client";

import { memo } from "react";
import { useRouter } from "next/navigation";
import {
    Calendar,
    Users,
    TrendingUp,
    Edit,
    Settings,
    Archive
} from "lucide-react";
import { Card, CardHeader, CardContent, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import type { Project} from "@/types";
import { ProjectStatus } from "@/types";
import { motion } from "framer-motion";

interface ProjectCardProps {
    project: Project;
    onEdit: (project: Project) => void;
    onArchive: (project: Project) => void;
}

const getStatusBadge = (status: ProjectStatus) => {
    const statusConfig = {
        [ProjectStatus.ACTIVE]: { label: "Active", color: "bg-emerald-500/20 text-emerald-400" },
        [ProjectStatus.ARCHIVED]: { label: "Archived", color: "bg-zinc-500/20 text-zinc-400" },
        [ProjectStatus.SUSPENDED]: { label: "Suspended", color: "bg-red-500/20 text-red-400" }
    };

    const config = statusConfig[status] || statusConfig[ProjectStatus.ACTIVE];
    return (
        <Badge className={config.color}>
            {config.label}
        </Badge>
    );
};

const getProgressPercentage = (stats?: Project["stats"]) => {
    if (!stats?.totalTasks) {return 0;}
    return Math.round((stats.completedTasks / stats.totalTasks) * 100);
};

export const ProjectCard = memo(function ProjectCard({
    project,
    onEdit,
    onArchive
}: ProjectCardProps) {
    const router = useRouter();

    return (
        <motion.div
            layout
            variants={{
                hidden: { opacity: 0, y: 20 },
                visible: { opacity: 1, y: 0 },
            }}
            exit={{ opacity: 0, scale: 0.95 }}
            whileHover={{ y: -5, transition: { duration: 0.2 } }}
            className="h-full"
        >
            <Card
                className="h-full border-white/10 bg-white/5 backdrop-blur-sm hover:bg-white/10 transition-colors group flex flex-col cursor-pointer focus-visible:ring-2 focus-visible:ring-indigo-500/50 outline-none"
                onClick={() => router.push(`/projects/${project.id}`)}
                role="button"
                tabIndex={0}
                aria-label={`View details for project ${project.name}`}
                onKeyDown={(e) => {
                    if (e.key === "Enter" || e.key === " ") {
                        e.preventDefault();
                        router.push(`/projects/${project.id}`);
                    }
                }}
            >
                <CardHeader className="pb-3">
                    <div className="flex items-start justify-between gap-4">
                        <div className="flex items-center gap-3 flex-1 min-w-0">
                            <div
                                className="h-10 w-10 rounded-lg flex items-center justify-center shadow-lg transition-transform group-hover:scale-110 duration-300"
                                style={{ backgroundColor: project.color }}
                            >
                                <span className="font-bold text-white text-sm">
                                    {project.name && typeof project.name === "string"
                                        ? project.name[0]
                                        : ""}
                                </span>
                            </div>
                            <div className="min-w-0 flex-1">
                                <CardTitle className="text-white text-lg truncate group-hover:text-indigo-400 transition-colors">
                                    {project.name}
                                </CardTitle>
                                <p className="text-sm text-zinc-400 mt-1">
                                    by {project.owner?.firstName} {project.owner?.lastName}
                                </p>
                            </div>
                        </div>
                        <div className="flex items-center gap-1">
                            {getStatusBadge(project.status)}
                        </div>
                    </div>
                </CardHeader>

                <CardContent className="space-y-4 flex-1 flex flex-col">
                    {project.description && (
                        <p className="text-sm text-zinc-300 line-clamp-2">
                            {project.description}
                        </p>
                    )}

                    {/* Progress */}
                    <div className="space-y-2">
                        <div className="flex justify-between text-sm">
                            <span className="text-zinc-400">Progress</span>
                            <span className="text-white font-medium">
                                {getProgressPercentage(project.stats)}%
                            </span>
                        </div>
                        <div className="h-2 rounded-full bg-white/10 overflow-hidden">
                            <div
                                className="h-full rounded-full transition-all duration-500 ease-out"
                                style={{
                                    width: `${getProgressPercentage(project.stats)}%`,
                                    backgroundColor: project.color,
                                }}
                            />
                        </div>
                    </div>

                    {/* Stats */}
                    <div className="grid grid-cols-3 gap-4 pt-2">
                        <div className="text-center">
                            <div className="flex items-center justify-center text-white mb-1">
                                <Calendar className="h-4 w-4 mr-1 text-indigo-400" />
                            </div>
                            <div className="text-lg font-semibold text-white">
                                {project.stats?.totalTasks || 0}
                            </div>
                            <div className="text-xs text-zinc-400">Tasks</div>
                        </div>
                        <div className="text-center">
                            <div className="flex items-center justify-center text-white mb-1">
                                <Users className="h-4 w-4 mr-1 text-emerald-400" />
                            </div>
                            <div className="text-lg font-semibold text-white">
                                {project.stats?.teamMembers || 0}
                            </div>
                            <div className="text-xs text-zinc-400">Members</div>
                        </div>
                        <div className="text-center">
                            <div className="flex items-center justify-center text-white mb-1">
                                <TrendingUp className="h-4 w-4 mr-1 text-amber-400" />
                            </div>
                            <div className="text-lg font-semibold text-white">
                                {project.stats?.recentActivity || 0}
                            </div>
                            <div className="text-xs text-zinc-400">Activity</div>
                        </div>
                    </div>

                    {/* Action Buttons */}
                    <div className="grid grid-cols-3 gap-2 pt-2 mt-auto opacity-100 lg:opacity-0 lg:group-hover:opacity-100 transition-all duration-300 transform translate-y-0 lg:translate-y-2 lg:group-hover:translate-y-0">
                        <Button
                            variant="ghost"
                            size="sm"
                            aria-label="Edit Project"
                            className="bg-transparent border border-white/10 text-zinc-400 hover:text-white hover:bg-white/10 hover:border-white/20 cursor-pointer"
                            onClick={(e) => {
                                e.stopPropagation();
                                onEdit(project);
                            }}
                        >
                            <Edit className="h-4 w-4" aria-hidden="true" />
                        </Button>
                        <Button
                            variant="ghost"
                            size="sm"
                            aria-label="Project Settings"
                            className="bg-transparent border border-white/10 text-zinc-400 hover:text-white hover:bg-white/10 hover:border-white/20 cursor-pointer"
                            onClick={(e) => {
                                e.stopPropagation();
                                router.push(`/projects/${project.id}/settings`);
                            }}
                        >
                            <Settings className="h-4 w-4" aria-hidden="true" />
                        </Button>
                        <Button
                            variant="ghost"
                            size="sm"
                            aria-label="Archive Project"
                            className="bg-transparent border border-white/10 text-zinc-400 hover:text-white hover:bg-white/10 hover:border-white/20 cursor-pointer"
                            onClick={(e) => {
                                e.stopPropagation();
                                onArchive(project);
                            }}
                        >
                            <Archive className="h-4 w-4" aria-hidden="true" />
                        </Button>
                    </div>
                </CardContent>
            </Card>
        </motion.div>
    );
});
