import React from "react";
import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { TeamList } from "@/components/analytics/TeamList";
import { TaskItem } from "@/components/tasks/TaskItem";
import { UserFilters } from "@/app/users/components/UserFilters";
import { TaskPriority, TaskStatus, TaskType, type Task } from "@/types";

vi.mock("next/image", () => ({
  default: (props: React.ImgHTMLAttributes<HTMLImageElement>) => <img {...props} alt={props.alt ?? ""} />,
}));

vi.mock("next/link", () => ({
  default: ({ children, href }: { children: React.ReactNode; href: string }) => (
    <a href={href}>{children}</a>
  ),
}));

const makeTask = (status: TaskStatus, priority: TaskPriority): Task => ({
  id: `${status}-${priority}`,
  title: `${status} task`,
  description: "Task description",
  status,
  priority,
  type: TaskType.FEATURE,
  projectId: "project-1",
  project: { name: "Project One" } as Task["project"],
  reporterId: "user-1",
  reporter: {} as Task["reporter"],
  tags: [],
  attachments: [],
  comments: [],
  history: [],
  progress: 0,
  subtasks: [],
  dependencies: [],
  customFields: {},
  createdAt: "2026-08-01T00:00:00.000Z",
  updatedAt: "2026-08-01T00:00:00.000Z",
});

describe("task and filter component branches", () => {
  it("maps all task status and priority colors while rendering actions", () => {
    const onToggleMenu = vi.fn();
    const onEdit = vi.fn();
    const onDelete = vi.fn();
    const onClick = vi.fn();
    const statuses = [
      TaskStatus.DONE,
      TaskStatus.IN_PROGRESS,
      TaskStatus.IN_REVIEW,
      TaskStatus.CANCELLED,
      TaskStatus.TODO,
    ];
    const priorities = [
      TaskPriority.URGENT,
      TaskPriority.HIGH,
      TaskPriority.MEDIUM,
      TaskPriority.LOW,
    ];

    render(
      <>
        {statuses.map((status, index) => (
          <TaskItem
            key={status}
            task={makeTask(status, priorities[index % priorities.length])}
            showProjectName
            isOpen={index === 0}
            isDeleting={index === 0}
            onToggleMenu={onToggleMenu}
            onEdit={onEdit}
            onDelete={onDelete}
            onClick={onClick}
          />
        ))}
      </>,
    );

    expect(screen.getByText("done task")).toBeInTheDocument();
    expect(screen.getAllByText("Project One")).not.toHaveLength(0);
    expect(screen.getByText("Edit Task")).toBeInTheDocument();
    fireEvent.click(screen.getAllByRole("button", { name: "Task actions" })[0]);
    expect(onToggleMenu).toHaveBeenCalled();
  });

  it("renders team efficiency states and the empty state", () => {
    const { rerender } = render(
      <TeamList
        team={[
          { name: "Ada Lovelace", tasks: 10, completed: 9, efficiency: 90, avatar: "ada.png" },
          { name: "Grace Hopper", tasks: 10, completed: 8, efficiency: 75 },
          { name: "Linus Torvalds", tasks: 10, completed: 4, efficiency: 40 },
        ]}
      />,
    );

    expect(screen.getByText("Ada Lovelace")).toBeInTheDocument();
    expect(screen.getByText("75%")).toBeInTheDocument();
    expect(screen.getByText("40%")).toBeInTheDocument();

    rerender(<TeamList team={[]} />);
    expect(screen.getByText("No team data available")).toBeInTheDocument();
  });

  it("renders idle, clear, and searching user-filter indicators", () => {
    const onSearchChange = vi.fn();
    const commonProps = {
      onSearchChange,
      roleFilter: "all" as const,
      onRoleFilterChange: vi.fn(),
      statusFilter: "all" as const,
      onStatusFilterChange: vi.fn(),
    };
    const { rerender } = render(
      <UserFilters {...commonProps} searchQuery="" debouncedSearchQuery="" />,
    );
    expect(screen.getByText("/")).toBeInTheDocument();

    rerender(
      <UserFilters {...commonProps} searchQuery="ada" debouncedSearchQuery="ada" />,
    );
    fireEvent.click(screen.getByRole("button", { name: "Clear search" }));
    expect(onSearchChange).toHaveBeenCalledWith("");

    rerender(
      <UserFilters {...commonProps} searchQuery="ada" debouncedSearchQuery="" isLoading />,
    );
    expect(document.querySelector(".animate-spin")).toBeInTheDocument();
  });
});
