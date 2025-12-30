import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { projectsApi } from "@/lib/api-endpoints";
import type {
  CreateProjectRequest,
  UpdateProjectRequest,
  Project,
} from "@/types";
import { ProjectStatus } from "@/types";
import { transformProjectData } from "@/lib/project-utils";
import { useAuthStore } from "@/stores/auth-store";
import { toast } from "sonner";
import { getErrorMessage } from "@/lib/error-utils";

// Type for API data with members
interface ApiProjectData extends CreateProjectRequest {
  members?: Array<{ userId: string; role: string }>;
  memberIds?: string[];
}

// Type for update API data
interface ApiUpdateProjectData extends UpdateProjectRequest {
  is_active?: boolean;
}

export function useProjects(options?: { enabled?: boolean }) {
  const { user } = useAuthStore();

  return useQuery({
    queryKey: ["projects"],
    queryFn: async () => {
      // Fetch up to 100 projects default
      const data = await projectsApi.getProjects(0, 100, false);
      // Transform data
      return Array.isArray(data)
        ? data.map((p: Project, index: number) =>
            transformProjectData(p, user ?? undefined, index),
          )
        : [];
    },
    enabled:
      options?.enabled !== undefined ? options.enabled && !!user : !!user, // Only fetch if user is logged in
    staleTime: 60 * 1000, // 1 minute
  });
}

export function useCreateProject() {
  const queryClient = useQueryClient();
  const { user } = useAuthStore();

  return useMutation({
    mutationFn: async (data: CreateProjectRequest) => {
      // Map memberIds to members logic if needed by backend, handled in API usually
      // But page.tsx did some manual mapping:
      const apiData: ApiProjectData = { ...data };
      if (apiData.memberIds && Array.isArray(apiData.memberIds)) {
        apiData.members = apiData.memberIds.map((userId: string) => ({
          userId,
          role: "member",
        }));
        delete apiData.memberIds;
      }

      const response = await projectsApi.createProject(apiData);
      return transformProjectData(response, user ?? undefined);
    },
    onSuccess: (newProject) => {
      queryClient.setQueryData(["projects"], (old: Project[] | undefined) => {
        return old ? [...old, newProject] : [newProject];
      });
      toast.success("Project created", {
        description: `Project "${newProject.name}" has been created successfully.`,
      });
    },
    onError: (error) => {
      toast.error("Failed to create project", {
        description: getErrorMessage(error),
      });
    },
  });
}

export function useUpdateProject() {
  const queryClient = useQueryClient();
  const { user } = useAuthStore();

  return useMutation({
    mutationFn: async ({
      id,
      data,
    }: {
      id: string;
      data: UpdateProjectRequest;
    }) => {
      const apiData: ApiUpdateProjectData = { ...data };
      // Map status to is_active
      if (apiData.status) {
        apiData.is_active = apiData.status === ProjectStatus.ACTIVE;
        delete apiData.status;
      }

      const response = await projectsApi.updateProject(id, apiData);
      // The backend might return the updated project or just success.
      // Assuming it returns updated project or we re-fetch.
      // If response is the project, transform it:
      if (response?.id) {
        return transformProjectData(response, user ?? undefined);
      }
      return null;
    },
    onSuccess: () => {
      // Removed unused vars
      queryClient.invalidateQueries({ queryKey: ["projects"] });

      toast.success("Project updated", {
        description: "Project has been updated successfully.",
      });
    },
    onError: (error) => {
      toast.error("Failed to update project", {
        description: getErrorMessage(error),
      });
    },
  });
}

export function useArchiveProject() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (project: Project) => {
      // API call
      await projectsApi.updateProject(project.id, { is_active: false } as ApiUpdateProjectData);
      return project;
    },
    onMutate: async (project) => {
      // Optimistic update
      await queryClient.cancelQueries({ queryKey: ["projects"] });
      const previousProjects = queryClient.getQueryData<Project[]>([
        "projects",
      ]);

      queryClient.setQueryData(["projects"], (old: Project[] | undefined) => {
        return old
          ? old.map((p) =>
              p.id === project.id
                ? { ...p, status: ProjectStatus.ARCHIVED }
                : p,
            )
          : [];
      });

      return { previousProjects };
    },
    onError: (err, newProject, context) => {
      queryClient.setQueryData(["projects"], context?.previousProjects);
      toast.error("Failed to archive project", {
        description: getErrorMessage(err),
      });
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ["projects"] });
    },
    onSuccess: (data, variables) => {
      toast.success("Project archived", {
        description: `Project "${variables.name}" has been moved to archive.`,
      });
    },
  });
}
