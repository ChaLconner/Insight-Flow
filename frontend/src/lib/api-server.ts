/* eslint-disable @typescript-eslint/no-explicit-any */
import { cookies } from "next/headers";
import type { Task } from "@/types";
import { transformProjectData } from "@/lib/project-utils";

// Use backend directly for server-side fetching to avoid loopback overhead and URL issues
const SERVER_BASE_URL = process.env.API_URL ?? "http://localhost:8000";

async function fetchServer<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const cookieStore = await cookies();
  const allCookies = cookieStore
    .getAll()
    .map((c) => `${c.name}=${c.value}`)
    .join("; ");

  // Standardize path to ensure it starts with / but doesn't duplicate
  const cleanPath = path.startsWith("/") ? path : `/${path}`;

  const res = await fetch(`${SERVER_BASE_URL}${cleanPath}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      Cookie: allCookies,
      ...options.headers,
    },
    cache: "no-store", // Default to dynamic for authenticated data
  });

  if (!res.ok) {
    // We can enhance this to throw specific errors or return null
    if (res.status === 404) {
      throw new Error("Not Found");
    }
    if (res.status === 401) {
      throw new Error("Unauthorized");
    }
    throw new Error(`API Error: ${res.status} ${res.statusText}`);
  }

  const data = await res.json();
  return data;
}

export const serverApi = {
  getProjects: async () => {
    const data: any[] = await fetchServer("/projects");
    return Array.isArray(data)
      ? data.map((p, index) => transformProjectData(p, undefined, index))
      : [];
  },
  getProject: async (id: string) => {
    const data = await fetchServer(`/projects/${id}`);
    return transformProjectData(data, undefined);
  },
  getProjectTasks: (projectId: string) =>
    fetchServer<Task[]>(`/projects/${projectId}/tasks?limit=50`),
  getTask: (id: string) => fetchServer<Task>(`/tasks/${id}`),
};
