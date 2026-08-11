import React from "react";
import { differenceInDays, isPast, isToday, isTomorrow } from "date-fns";
import type { TaskPriority, TaskStatus, TaskType, UpdateTaskRequest } from "@/types";

export const buildTaskUpdateRequest = (input: {
  title: string;
  description: string;
  priority: TaskPriority;
  status: TaskStatus;
  type: TaskType;
  tags: string;
  dueDate: string;
  estimatedHours: string;
  actualHours: string;
}): UpdateTaskRequest => ({
  title: input.title,
  description: input.description,
  priority: input.priority,
  status: input.status,
  type: input.type,
  tags: input.tags
    .split(",")
    .map((tag) => tag.trim())
    .filter(Boolean),
  dueDate: input.dueDate ? new Date(input.dueDate).toISOString() : undefined,
  estimatedHours: input.estimatedHours ? Number.parseFloat(input.estimatedHours) : undefined,
  actualHours: input.actualHours ? Number.parseFloat(input.actualHours) : undefined,
});

export const getDueDateIconColor = (dueDate: string | null | undefined): string => {
  if (!dueDate) {
    return "text-zinc-400";
  }
  const date = new Date(dueDate);
  if (isPast(date) && !isToday(date)) {
    return "text-red-500 dark:text-red-400";
  }
  if (differenceInDays(date, new Date()) <= 2) {
    return "text-amber-500 dark:text-amber-400";
  }
  return "text-blue-500 dark:text-blue-400";
};

export const getDueDateBadgeColor = (dueDate: string): string => {
  const date = new Date(dueDate);
  if (isPast(date) && !isToday(date)) {
    return "bg-red-100 dark:bg-red-500/20 text-red-600 dark:text-red-400";
  }
  if (isToday(date) || isTomorrow(date)) {
    return "bg-amber-100 dark:bg-amber-500/20 text-amber-600 dark:text-amber-400";
  }
  return "bg-blue-100 dark:bg-blue-500/20 text-blue-600 dark:text-blue-400";
};

export const getDueDateLabel = (dueDate: string): string => {
  const date = new Date(dueDate);
  if (isPast(date) && !isToday(date)) {
    return "Overdue";
  }
  if (isToday(date)) {
    return "Today";
  }
  if (isTomorrow(date)) {
    return "Tomorrow";
  }
  return `${differenceInDays(date, new Date())} days left`;
};

export const renderDescription = (text: string) => {
  if (!text) {
    return (
      <span className="text-muted-foreground/60 italic">No description provided.</span>
    );
  }

  const lines = text.split("\n");
  const elements: JSX.Element[] = [];
  let listBuffer: JSX.Element[] = [];
  let inList = false;
  let listType = "ul";

  lines.forEach((line) => {
    const trimmed = line.trim();
    const isBullet = trimmed.startsWith("- ") || trimmed.startsWith("* ");
    const isNumber = /^\d+\.\s/.test(trimmed);

    if (isBullet || isNumber) {
      if (!inList) {
        inList = true;
        listType = isNumber ? "ol" : "ul";
      }
      const content = trimmed.replace(/^(?:[-*] |\d+\.\s)/, "");
      listBuffer.push(
        <li key={`li-${content}-${listBuffer.length}`} className="ml-4 pl-1">
          {content}
        </li>,
      );
    } else {
      if (inList) {
        elements.push(
          listType === "ul" ? (
            <ul key={`ul-${elements.length}`} className="list-disc mb-4 space-y-1">
              {listBuffer}
            </ul>
          ) : (
            <ol key={`ol-${elements.length}`} className="list-decimal mb-4 space-y-1">
              {listBuffer}
            </ol>
          ),
        );
        listBuffer = [];
        inList = false;
      }
      if (trimmed) {
        elements.push(
          <p key={`p-${line}-${elements.length}`} className="mb-2 min-h-[1.5em]">
            {line}
          </p>,
        );
      } else {
        elements.push(<br key={`br-${elements.length}`} />);
      }
    }
  });
  if (inList && listBuffer.length > 0) {
    elements.push(
      listType === "ul" ? (
        <ul key="ul-last" className="list-disc mb-4 space-y-1">
          {listBuffer}
        </ul>
      ) : (
        <ol key="ol-last" className="list-decimal mb-4 space-y-1">
          {listBuffer}
        </ol>
      ),
    );
  }
  return (
    <div className="text-muted-foreground leading-relaxed text-[15px]">{elements}</div>
  );
};
