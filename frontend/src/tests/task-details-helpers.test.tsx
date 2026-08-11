import React from "react";
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import {
  buildTaskUpdateRequest,
  getDueDateBadgeColor,
  getDueDateIconColor,
  getDueDateLabel,
  renderDescription,
} from "@/components/tasks/task-details-helpers";
import { TaskPriority, TaskStatus, TaskType } from "@/types";

const daysFromNow = (days: number) => new Date(Date.now() + days * 24 * 60 * 60 * 1000).toISOString();

describe("TaskDetails helpers", () => {
  it("builds update requests with normalized tags and numeric fields", () => {
    const result = buildTaskUpdateRequest({
      title: "Updated task",
      description: "Details",
      priority: TaskPriority.HIGH,
      status: TaskStatus.IN_PROGRESS,
      type: TaskType.FEATURE,
      tags: "frontend, , quality",
      dueDate: "2026-08-20",
      estimatedHours: "2.5",
      actualHours: "",
    });

    expect(result).toMatchObject({
      title: "Updated task",
      tags: ["frontend", "quality"],
      estimatedHours: 2.5,
      actualHours: undefined,
    });
    expect(result.dueDate).toContain("2026-08-20");
  });

  it("covers due-date color and label branches", () => {
    const overdue = daysFromNow(-3);
    const soon = daysFromNow(1);
    const later = daysFromNow(5);

    expect(getDueDateIconColor(undefined)).toBe("text-zinc-400");
    expect(getDueDateIconColor(overdue)).toContain("red");
    expect(getDueDateIconColor(soon)).toContain("amber");
    expect(getDueDateIconColor(later)).toContain("blue");

    expect(getDueDateBadgeColor(overdue)).toContain("red");
    expect(getDueDateBadgeColor(soon)).toContain("amber");
    expect(getDueDateBadgeColor(later)).toContain("blue");

    expect(getDueDateLabel(overdue)).toBe("Overdue");
    expect(getDueDateLabel(new Date().toISOString())).toBe("Today");
    expect(getDueDateLabel(daysFromNow(1))).toBe("Tomorrow");
    expect(getDueDateLabel(later)).toMatch(/days left/);
  });

  it("renders empty descriptions, paragraphs, and ordered or unordered lists", () => {
    const { container } = render(
      <>
        {renderDescription("")}
        {renderDescription("First line\n\n- bullet one\n* bullet two\n\n1. numbered")}
      </>,
    );

    expect(screen.getByText("No description provided.")).toBeInTheDocument();
    expect(screen.getByText("First line")).toBeInTheDocument();
    expect(screen.getByText("bullet one")).toBeInTheDocument();
    expect(screen.getByText("numbered")).toBeInTheDocument();
    expect(container.querySelector("ul")).toBeInTheDocument();
    expect(container.querySelector("ol")).toBeInTheDocument();
  });
});
