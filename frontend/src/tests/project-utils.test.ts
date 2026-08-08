import { describe, expect, it } from "vitest";
import { getProjectColor, transformProjectData } from "@/lib/project-utils";

describe("project color mapping", () => {
  it("cycles legacy default colors by project position", () => {
    expect(getProjectColor("#6366f1", 0)).toBe("#6366f1");
    expect(getProjectColor("#6366f1", 1)).toBe("#10b981");
    expect(getProjectColor(undefined, 2)).toBe("#f59e0b");
  });

  it("preserves explicitly selected colors", () => {
    expect(getProjectColor("#ec4899", 0)).toBe("#ec4899");
  });

  it("applies same fallback to full project-list data", () => {
    const project = transformProjectData(
      { id: "project-2", name: "Project 2", color: "#6366f1" },
      undefined,
      2,
    );

    expect(project.color).toBe("#f59e0b");
  });
});
