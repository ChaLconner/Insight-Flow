import { beforeEach, describe, expect, it, vi } from "vitest";
import { TaskPriority, TaskType, UserRole } from "@/types";

const apiClientMock = {
  get: vi.fn(),
  post: vi.fn(),
  put: vi.fn(),
  patch: vi.fn(),
  delete: vi.fn(),
};

const createDeduplicatedRequestMock = vi.fn(
  async <T>(requestFn: () => Promise<T>) => requestFn(),
);

vi.mock("@/lib/api-client", () => ({
  apiClient: apiClientMock,
  createDeduplicatedRequest: createDeduplicatedRequestMock,
}));

describe("api endpoints coverage", () => {
  beforeEach(async () => {
    vi.clearAllMocks();

    apiClientMock.get.mockResolvedValue({ data: { ok: true, projectIds: ["project-1"] } });
    apiClientMock.post.mockResolvedValue({ data: { ok: true } });
    apiClientMock.put.mockResolvedValue({ data: { ok: true } });
    apiClientMock.patch.mockResolvedValue({ data: { ok: true } });
    apiClientMock.delete.mockResolvedValue({ data: { ok: true } });

    const { __clearUsersSettingsCacheForTests } = await import("@/lib/api-endpoints");
    __clearUsersSettingsCacheForTests();
  });

  it("covers authentication and file endpoint calls", async () => {
    const { authApi, fileApi } = await import("@/lib/api-endpoints");

    await expect(authApi.login({ email: "user@example.com", password: "secret123" })).resolves.toEqual({
      ok: true,
    });
    await authApi.register({
      email: "user@example.com",
      username: "jane1234",
      password: "secret123",
      name: "Jane Doe",
      firstName: "Jane",
      lastName: "Doe",
    });
    await authApi.logout();
    await authApi.refreshToken("refresh-token");
    await authApi.getCurrentUser();
    await authApi.changePassword("old-secret", "new-secret");
    await authApi.forgotPassword("user@example.com");
    await authApi.resetPassword("reset-token", "new-secret");
    await authApi.validateResetToken("reset-token");

    const formData = new FormData();
    formData.append("file", new Blob(["hello"]), "hello.txt");

    await fileApi.uploadFile(formData);
    await fileApi.deleteFile("https://example.com/file.png");
    await fileApi.getFileInfo("https://example.com/file.png");

    expect(apiClientMock.post).toHaveBeenCalledWith("/auth/login", {
      email: "user@example.com",
      password: "secret123",
    });
    expect(apiClientMock.post).toHaveBeenCalledWith(
      "/files/upload",
      formData,
      expect.objectContaining({
        headers: { "Content-Type": "multipart/form-data" },
      }),
    );
  });

  it("covers task and project endpoint calls", async () => {
    const { tasksApi, projectsApi } = await import("@/lib/api-endpoints");

    await tasksApi.getTasks(5, 20, "bug", "open");
    await tasksApi.getMyTasks(0, 25, "design", "in_progress");
    await tasksApi.getTask("task-1");
    await tasksApi.getProjectTasks(
      "project-1",
      10,
      15,
      "priority",
      "asc",
      "launch",
      "todo",
    );
    await tasksApi.createTask("project-1", {
      title: "Ship",
      description: "Now",
      projectId: "project-1",
      priority: TaskPriority.MEDIUM,
      type: TaskType.FEATURE,
    });
    await tasksApi.updateTask("task-1", { title: "Updated" });
    await tasksApi.updateProjectTask("project-1", "task-1", { title: "Project Updated" });
    await tasksApi.deleteTask("task-1");
    await tasksApi.deleteProjectTask("project-1", "task-1");
    await tasksApi.updateTaskStatus("task-1", "done");
    await tasksApi.updateProjectTaskStatus("project-1", "task-1", "done");
    await tasksApi.assignTask("task-1", "user-2");
    await tasksApi.assignProjectTask("project-1", "task-1", "user-2");
    await tasksApi.getTaskComments("task-1");
    await tasksApi.createTaskComment("task-1", { content: "@sam please review" });

    await projectsApi.getProjects(0, 50, true, "roadmap", "active", "name");
    await projectsApi.getProject("project-1");
    await projectsApi.createProject({ name: "Roadmap", color: "#6366f1" });
    await projectsApi.updateProject("project-1", { name: "Roadmap v2" });
    await projectsApi.deleteProject("project-1");
    await projectsApi.getProjectMembers("project-1");
    await projectsApi.addProjectMember("project-1", { email: "member@example.com" });
    await projectsApi.removeProjectMember("project-1", "user-2");
    await projectsApi.updateMemberRole("project-1", "user-2", "admin");

    expect(createDeduplicatedRequestMock).toHaveBeenCalled();
    expect(apiClientMock.get).toHaveBeenCalledWith("/tasks/", {
      params: { skip: 5, limit: 20, search: "bug", status: "open" },
    });
    expect(apiClientMock.put).toHaveBeenCalledWith("/tasks/task-1/status", { status: "done" });
  });

  it("covers user, dashboard, analytics, notification, payment, and favorite endpoints", async () => {
    apiClientMock.get
      .mockResolvedValueOnce({ data: { id: "user-1" } })
      .mockResolvedValueOnce({ data: { id: "search-result" } })
      .mockResolvedValueOnce({ data: [{ id: "user-2" }] })
      .mockResolvedValueOnce({ data: { theme: "dark" } })
      .mockResolvedValueOnce({ data: { stats: true } })
      .mockResolvedValueOnce({ data: { stats: true } })
      .mockResolvedValueOnce({ data: [{ id: "project-1" }] })
      .mockResolvedValueOnce({ data: [{ id: "activity-1" }] })
      .mockResolvedValueOnce({ data: { overview: true } })
      .mockResolvedValueOnce({ data: { items: [] } })
      .mockResolvedValueOnce({ data: [{ id: "notification-1" }] })
      .mockResolvedValueOnce({ data: 4 })
      .mockResolvedValueOnce({ data: { plans: [] } })
      .mockResolvedValueOnce({ data: { payment_methods: [] } })
      .mockResolvedValueOnce({ data: { subscription: true } })
      .mockResolvedValueOnce({ data: { projectIds: ["project-1"] } });

    const {
      usersApi,
      dashboardApi,
      analyticsApi,
      notificationsApi,
      paymentApi,
      favoritesApi,
    } = await import("@/lib/api-endpoints");

    await usersApi.getCurrentUser();
    await usersApi.updateCurrentUser({ firstName: "Jane" });

    const avatarData = new FormData();
    avatarData.append("file", new Blob(["avatar"]), "avatar.png");
    await usersApi.uploadAvatar(avatarData);
    await usersApi.searchUserByEmail("user@example.com");
    await usersApi.searchUsers("jane", 5, 10, "admin", "active");
    await expect(usersApi.getSettings()).resolves.toEqual({ theme: "dark" });
    await expect(usersApi.getSettings()).resolves.toEqual({ theme: "dark" });
    await usersApi.updateSettings({ theme: "light" });
    await usersApi.inviteUser({ email: "invitee@example.com", role: UserRole.MEMBER });
    await usersApi.getStats();

    await dashboardApi.getOverview();
    await dashboardApi.getTodayTasks();
    await dashboardApi.getRecentProjects();
    await dashboardApi.getTeamActivity();

    await analyticsApi.getAnalytics("30d");
    await analyticsApi.getTeamWorkload({
      page: 2,
      pageSize: 25,
      search: "jane",
      sortBy: "name",
      sortOrder: "asc",
    });

    await notificationsApi.getNotifications(5, 25);
    await notificationsApi.getUnreadCount();
    await notificationsApi.markAsRead("notification-1");
    await notificationsApi.markAllAsRead();
    await notificationsApi.deleteNotification("notification-1");

    await paymentApi.getPlans();
    await paymentApi.getPaymentMethods();
    await paymentApi.createSetupIntent();
    await paymentApi.setDefaultPaymentMethod("pm_1");
    await paymentApi.deletePaymentMethod("pm_1");
    await paymentApi.getSubscription();
    await paymentApi.createSubscription({ plan: "pro" });
    await paymentApi.cancelSubscription(true);

    await expect(favoritesApi.getFavoriteIds()).resolves.toEqual(["project-1"]);
    await favoritesApi.toggleFavorite("project-1");
    await favoritesApi.addFavorite("project-1");
    await favoritesApi.removeFavorite("project-1");

    expect(apiClientMock.get).toHaveBeenCalledWith("/users/search", {
      params: { q: "jane", skip: 5, limit: 10, role: "admin", status: "active" },
    });
    expect(apiClientMock.patch).toHaveBeenCalledWith("/users/me/settings", { theme: "light" });
    expect(apiClientMock.get).toHaveBeenCalledTimes(17);
  });
});
