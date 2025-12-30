import { memo } from "react";
import { motion, AnimatePresence } from "framer-motion";
import type { Project } from "@/types";
import { ProjectCard } from "./ProjectCard";
import { Search, Plus } from "lucide-react";
import { Button } from "@/components/ui/button";

interface ProjectGridProps {
  projects: Project[];
  isLoading: boolean;
  onEdit: (project: Project) => void;
  onArchive: (project: Project) => void;
  onFavorite?: (project: Project) => void;
  favoriteIds?: Set<string>;
  hasFilters: boolean;
  onCreateProject: () => void;
}

export const ProjectGrid = memo(function ProjectGrid({
  projects,
  isLoading,
  onEdit,
  onArchive,
  onFavorite,
  favoriteIds = new Set(),
  hasFilters,
  onCreateProject,
}: ProjectGridProps) {
  // Empty State - only show when not loading and no projects found
  if (projects.length === 0 && !isLoading) {
    return (
      <div className="text-center py-12">
        <div className="mx-auto h-12 w-12 rounded-full bg-secondary flex items-center justify-center mb-4">
          <Search className="h-6 w-6 text-muted-foreground" />
        </div>
        <h3 className="text-lg font-medium text-foreground mb-2">
          No projects found
        </h3>
        <p className="text-muted-foreground mb-6">
          {hasFilters
            ? "Try adjusting your search or filter criteria."
            : "Get started by creating your first project."}
        </p>
        {!hasFilters && (
          <Button
            onClick={onCreateProject}
            className="bg-indigo-600 hover:bg-indigo-500 text-white cursor-pointer"
          >
            <Plus className="h-4 w-4 mr-2" />
            Create New Project
          </Button>
        )}
      </div>
    );
  }

  return (
    <motion.div
      className="grid gap-6 grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4"
      initial="hidden"
      animate="visible"
      variants={{
        hidden: { opacity: 0 },
        visible: {
          opacity: 1,
          transition: {
            staggerChildren: 0.03,
          },
        },
      }}
    >
      <AnimatePresence mode="popLayout">
        {projects.map((project) => (
          <ProjectCard
            key={project.id}
            project={project}
            onEdit={onEdit}
            onArchive={onArchive}
            onFavorite={onFavorite}
            isFavorite={favoriteIds.has(project.id)}
          />
        ))}
      </AnimatePresence>
    </motion.div>
  );
});
