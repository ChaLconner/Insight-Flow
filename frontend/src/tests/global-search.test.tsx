import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { Project, Task } from "@/types";
import { clearGlobalSearchCache, GlobalSearch } from "@/components/layout/GlobalSearch";
import { projectsApi, tasksApi } from "@/lib/api-endpoints";

const authState = vi.hoisted(() => ({
  isAuthenticated: true,
  user: { id: "user-a" as string } as { id: string } | null,
}));
const pushMock = vi.hoisted(() => vi.fn());

vi.mock("@/lib/api-endpoints", () => ({
  projectsApi: { getProjects: vi.fn() },
  tasksApi: { getMyTasks: vi.fn() },
}));

vi.mock("@/stores/auth-store", () => ({
  useAuthStore: (selector: (state: typeof authState) => unknown) => selector(authState),
}));

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: pushMock }),
}));

const project = { id: "project-1", name: "Alpha" } as unknown as Project;
const task = {
  id: "task-1",
  title: "Build Alpha",
  projectId: "project-1",
  project: { name: "Alpha" },
} as unknown as Task;

function searchFor(value: string) {
  const input = screen.getByRole("searchbox");
  fireEvent.focus(input);
  fireEvent.change(input, { target: { value } });
}

describe("GlobalSearch", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    clearGlobalSearchCache();
    authState.isAuthenticated = true;
    authState.user = { id: "user-a" };
  });

  it("loads and renders project and task results for the active user", async () => {
    vi.mocked(projectsApi.getProjects).mockResolvedValueOnce([project, project]);
    vi.mocked(tasksApi.getMyTasks).mockResolvedValueOnce([task]);
    const onSelect = vi.fn();

    render(<GlobalSearch onSelect={onSelect} />);
    searchFor("Alpha");

    await waitFor(() => {
      expect(projectsApi.getProjects).toHaveBeenCalledWith(0, 5, false, "Alpha");
      expect(tasksApi.getMyTasks).toHaveBeenCalledWith(0, 5, "Alpha");
    });

    expect(screen.getByRole("button", { name: "Alpha" })).toBeInTheDocument();
    expect(screen.getByText("Build Alpha")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Alpha" }));

    expect(pushMock).toHaveBeenCalledWith("/projects/project-1");
    expect(onSelect).toHaveBeenCalled();
  });

  it("scopes cached results to the current user", async () => {
    vi.mocked(projectsApi.getProjects).mockResolvedValue([project]);
    vi.mocked(tasksApi.getMyTasks).mockResolvedValue([]);

    const first = render(<GlobalSearch />);
    searchFor("Alpha");
    await waitFor(() => expect(projectsApi.getProjects).toHaveBeenCalledTimes(1));
    first.unmount();

    authState.user = { id: "user-b" };
    render(<GlobalSearch />);
    searchFor("Alpha");

    await waitFor(() => expect(projectsApi.getProjects).toHaveBeenCalledTimes(2));
  });

  it("uses the standalone-task fallback route", async () => {
    const standaloneTask = { id: "task-2", title: "Standalone task" } as unknown as Task;
    vi.mocked(projectsApi.getProjects).mockResolvedValueOnce([]);
    vi.mocked(tasksApi.getMyTasks).mockResolvedValueOnce([standaloneTask]);

    render(<GlobalSearch />);
    searchFor("task");
    await waitFor(() => expect(screen.getByText("Standalone task")).toBeInTheDocument());

    fireEvent.click(screen.getByRole("button", { name: "Standalone task" }));
    expect(pushMock).toHaveBeenCalledWith("/projects?tab=tasks&search=Standalone%20task");
  });

  it("shows no results after a failed search and skips unauthenticated requests", async () => {
    const consoleError = vi.spyOn(console, "error").mockImplementation(() => {});
    vi.mocked(projectsApi.getProjects).mockRejectedValueOnce(new Error("offline"));
    vi.mocked(tasksApi.getMyTasks).mockResolvedValueOnce([]);

    const first = render(<GlobalSearch />);
    searchFor("offline");
    await waitFor(() => expect(screen.getByText("No results found.")).toBeInTheDocument());

    first.unmount();
    clearGlobalSearchCache();
    authState.isAuthenticated = false;
    render(<GlobalSearch />);
    searchFor("blocked");
    expect(projectsApi.getProjects).toHaveBeenCalledTimes(1);
    expect(tasksApi.getMyTasks).toHaveBeenCalledTimes(1);
    consoleError.mockRestore();
  });
});
