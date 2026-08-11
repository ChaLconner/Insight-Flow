"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { DashboardLayout } from "@/components/layout/DashboardLayout";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
  Button,
  Input,
  Textarea,
  Skeleton,
} from "@/components/ui";
import { projectsApi } from "@/lib/api-endpoints";
import type { Project } from "@/types";
import { toast } from "sonner";
import { getErrorMessage } from "@/lib/error-utils";
import { ArrowLeft, Save, Trash2 } from "lucide-react";

import { DeleteProjectModal } from "@/components/modals/DeleteProjectModal";

export default function ProjectSettingsPage() {
  const params = useParams();
  const router = useRouter();
  const projectId = params.id as string;
  const [project, setProject] = useState<Project | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Form state
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");

  // Modal state
  const [isDeleteModalOpen, setIsDeleteModalOpen] = useState(false);

  useEffect(() => {
    const fetchProject = async () => {
      try {
        setLoading(true);
        const data = await projectsApi.getProject(projectId);
        setProject(data);
        setName(data.name);
        setDescription(data.description ?? "");
      } catch (err) {
        console.error("Failed to fetch project:", err);
        setError("Failed to load project details");
      } finally {
        setLoading(false);
      }
    };

    if (projectId) {
      fetchProject();
    }
  }, [projectId]);

  const handleSave = async () => {
    if (!project) {
      return;
    }

    try {
      setSaving(true);
      await projectsApi.updateProject(project.id, {
        name,
        description,
      });
      router.push(`/projects/${project.id}`);
      toast.success("Project updated successfully");
    } catch (err) {
      console.error("Failed to update project:", err);
      setError("Failed to update project");
      toast.error("Failed to update project", {
        description: getErrorMessage(err),
      });
    } finally {
      setSaving(false);
    }
  };

  const handleDeleteClick = () => {
    setIsDeleteModalOpen(true);
  };

  const handleConfirmDelete = async () => {
    if (!project) {
      return;
    }

    try {
      setSaving(true);
      await projectsApi.deleteProject(project.id);
      toast.success("Project deleted successfully");
      router.push("/projects");
    } catch (err) {
      console.error("Failed to delete project:", err);
      toast.error("Failed to delete project", {
        description: getErrorMessage(err),
      });
      setSaving(false);
      setIsDeleteModalOpen(false);
    }
  };

  if (loading) {
    return (
      <DashboardLayout>
        <div className="space-y-6 max-w-2xl mx-auto">
          <Skeleton className="h-10 w-48" />
          <Skeleton className="h-96 w-full" />
        </div>
      </DashboardLayout>
    );
  }

  // eslint-disable-next-line @typescript-eslint/prefer-nullish-coalescing
  if (error || !project) {
    return (
      <DashboardLayout>
        <div className="flex flex-col items-center justify-center h-[60vh] space-y-4">
          <h2 className="text-2xl font-bold text-foreground">Error</h2>
          <p className="text-muted-foreground">{error ?? "Project not found"}</p>
          <Button onClick={() => router.push("/projects")}>
            Back to Projects
          </Button>
        </div>
      </DashboardLayout>
    );
  }

  return (
    <DashboardLayout>
      <div className="max-w-2xl mx-auto space-y-8">
        <div className="flex items-center gap-2">
          <Button
            variant="ghost"
            size="sm"
            className="p-0 h-auto hover:bg-transparent text-muted-foreground hover:text-foreground"
            onClick={() => router.push(`/projects/${projectId}`)}
          >
            <ArrowLeft className="h-4 w-4 mr-1" />
            Back to Project
          </Button>
        </div>

        <div>
          <h1 className="text-3xl font-bold text-foreground">Project Settings</h1>
          <p className="text-muted-foreground">Manage your project configuration.</p>
        </div>

        <Card className="border-border bg-card backdrop-blur-sm">
          <CardHeader>
            <CardTitle className="text-foreground">General Information</CardTitle>
            <CardDescription className="text-muted-foreground">
              Update your project's name and description.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <label htmlFor="project-name" className="text-sm font-medium text-foreground">
                Project Name
              </label>
              <Input
                id="project-name"
                value={name}
                onChange={(e) => setName(e.target.value)}
                className="bg-background border-border text-foreground"
              />
            </div>
            <div className="space-y-2">
              <label htmlFor="project-description" className="text-sm font-medium text-foreground">
                Description
              </label>
              <Textarea
                id="project-description"
                value={description}
                onChange={(e: React.ChangeEvent<HTMLTextAreaElement>) =>
                  setDescription(e.target.value)
                }
                className="bg-background border-border text-foreground min-h-[100px]"
              />
            </div>
            <div className="pt-4 flex justify-end">
              <Button
                onClick={handleSave}
                disabled={saving}
                className="bg-primary hover:bg-primary/90 text-primary-foreground"
              >
                {saving ? (
                  "Saving..."
                ) : (
                  <>
                    <Save className="mr-2 h-4 w-4" />
                    Save Changes
                  </>
                )}
              </Button>
            </div>
          </CardContent>
        </Card>

        <Card className="border-destructive/50 bg-destructive/10 backdrop-blur-sm">
          <CardHeader>
            <CardTitle className="text-destructive">Danger Zone</CardTitle>
            <CardDescription className="text-destructive/80">
              Irreversible actions for this project.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex items-center justify-between">
              <div>
                <h4 className="text-sm font-medium text-destructive">
                  Delete Project
                </h4>
                <p className="text-xs text-destructive/80">
                  Once deleted, all data associated with this project will be
                  permanently removed.
                </p>
              </div>
              <Button
                variant="destructive"
                onClick={handleDeleteClick}
                disabled={saving}
              >
                <Trash2 className="mr-2 h-4 w-4" />
                Delete Project
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>

      <DeleteProjectModal
        isOpen={isDeleteModalOpen}
        onClose={() => setIsDeleteModalOpen(false)}
        onConfirm={handleConfirmDelete}
        project={project}
        isDeleting={saving}
      />
    </DashboardLayout>
  );
}
