"use client";

import React, { memo } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Briefcase } from "lucide-react";
import { ProjectCard } from "./ProjectCard";
import type { ProjectCardProject } from "./ProjectCard";
import Link from "next/link";

interface RecentProjectsProps {
  projects: ProjectCardProject[];
}

const RecentProjects = memo(function RecentProjects({
  projects,
}: RecentProjectsProps) {
  return (
    <Card className="col-span-4 border-border bg-card">
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle className="text-lg font-semibold text-foreground">
          Recent Projects
        </CardTitle>
        <Button
          variant="ghost"
          size="sm"
          className="text-muted-foreground hover:text-foreground cursor-pointer"
          asChild
        >
          <Link href="/projects">View All</Link>
        </Button>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          {projects.length > 0 ? (
            projects.map((project) => (
              <ProjectCard key={project.id} project={project} />
            ))
          ) : (
            <EmptyProjectsState />
          )}
        </div>
      </CardContent>
    </Card>
  );
});

// Separate empty state component - memoized
const EmptyProjectsState = memo(function EmptyProjectsState() {
  return (
    <div className="text-center text-muted-foreground py-12">
      <div className="mx-auto h-12 w-12 rounded-full bg-muted flex items-center justify-center mb-3">
        <Briefcase className="h-6 w-6 text-muted-foreground" />
      </div>
      <p className="font-medium text-foreground">No projects yet</p>
      <p className="text-sm mt-1">Create your first project to get started!</p>
    </div>
  );
});

RecentProjects.displayName = "RecentProjects";
EmptyProjectsState.displayName = "EmptyProjectsState";

export { RecentProjects };
