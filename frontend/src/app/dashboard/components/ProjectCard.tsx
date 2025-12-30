"use client";

import React, { memo } from "react";
import { Badge } from "@/components/ui/badge";
import Link from "next/link";

// Static class names
const PROJECT_ITEM_CLASSES =
  "group p-3 rounded-xl bg-muted/20 hover:bg-muted/40 transition-all cursor-pointer";
const ICON_CONTAINER_CLASSES =
  "h-12 w-12 rounded-xl flex items-center justify-center shadow-lg transition-transform group-hover:scale-105 duration-300 shrink-0";

export interface ProjectCardProject {
  id: string;
  name: string;
  description?: string | null;
  progress?: number;
  color?: string;
  status?: "active" | "archived" | "suspended";
}

interface ProjectCardProps {
  project: ProjectCardProject;
}

// Map status to badge variant and text
const STATUS_CONFIG = {
  active: {
    label: "Active",
    className: "bg-emerald-500/10 text-emerald-400 border-emerald-500/20",
  },
  archived: {
    label: "Archived",
    className: "bg-zinc-500/10 text-zinc-400 border-zinc-500/20",
  },
  suspended: {
    label: "Suspended",
    className: "bg-red-500/10 text-red-400 border-red-500/20",
  },
} as const;

const ProjectCard = memo(function ProjectCard({ project }: ProjectCardProps) {
  const projectColor = project.color ?? "#6366f1";
  const projectProgress = project.progress ?? 0;
  const projectInitial =
    project.name && typeof project.name === "string" ? project.name[0] : "";
  const statusConfig = STATUS_CONFIG[project.status ?? "active"];

  return (
    <Link href={`/projects/${project.id}`}>
      <div className={PROJECT_ITEM_CLASSES}>
        <div className="flex flex-col sm:flex-row sm:items-center gap-4">
          {/* Icon & Title */}
          <div className="grid grid-cols-[auto_minmax(0,1fr)] gap-4 w-full sm:w-auto sm:flex-1 items-center">
            <div
              className={ICON_CONTAINER_CLASSES}
              style={{ backgroundColor: projectColor }}
            >
              <span className="font-bold text-white text-lg">
                {projectInitial}
              </span>
            </div>
            <div className="min-w-0 overflow-hidden w-full">
              <h4 className="font-semibold text-foreground text-base truncate group-hover:text-primary transition-colors">
                {project.name}
              </h4>
              <p className="text-sm text-muted-foreground truncate">
                {project.description ?? "No description"}
              </p>
            </div>
          </div>

          {/* Status & Progress */}
          <div className="flex items-center justify-between sm:justify-end gap-4 w-full sm:w-auto mt-2 sm:mt-0">
            <div className="flex-1 sm:flex-none sm:w-32">
              <div className="flex justify-between text-xs mb-1.5">
                <span className="text-muted-foreground">Progress</span>
                <span className="text-foreground font-medium">
                  {projectProgress}%
                </span>
              </div>
              <div className="h-1.5 w-full rounded-full bg-muted overflow-hidden">
                <div
                  className="h-full rounded-full transition-all duration-500"
                  style={{
                    width: `${projectProgress}%`,
                    backgroundColor: projectColor,
                  }}
                />
              </div>
            </div>
            <Badge
              variant="secondary"
              className={`shrink-0 cursor-pointer ${statusConfig.className}`}
            >
              {statusConfig.label}
            </Badge>
          </div>
        </div>
      </div>
    </Link>
  );
});

ProjectCard.displayName = "ProjectCard";

export { ProjectCard };
