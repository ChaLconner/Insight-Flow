import React from "react";
import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

const usersApiMock = {
  getSettings: vi.fn(),
  updateSettings: vi.fn(),
};

const toastErrorMock = vi.fn();

vi.mock("@/lib/api-endpoints", () => ({
  usersApi: usersApiMock,
}));

vi.mock("sonner", () => ({
  toast: {
    error: toastErrorMock,
  },
}));

describe("NotificationsSettings", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.useRealTimers();
  });

  it("loads saved notification preferences from user settings", async () => {
    usersApiMock.getSettings.mockResolvedValue({
      notificationPreferences: {
        inApp: {
          tasks: false,
          projects: true,
          mentions: false,
          updates: true,
          system: true,
        },
        email: {
          tasks: true,
          projects: false,
          mentions: true,
        },
      },
    });

    const { NotificationsSettings } = await import(
      "@/app/settings/components/notifications-settings"
    );

    render(<NotificationsSettings />);

    expect(await screen.findByText("3 of 5 enabled")).toBeInTheDocument();
    expect(screen.getByText("2 of 3 enabled")).toBeInTheDocument();

    const toggles = screen.getAllByRole("checkbox");
    expect(toggles).toHaveLength(8);
    expect(toggles[0]).not.toBeChecked();
    expect(toggles[1]).toBeChecked();
    expect(toggles[5]).toBeChecked();
    expect(toggles[6]).not.toBeChecked();
  });

  it("autosaves updated in-app preferences after toggle", async () => {
    vi.useRealTimers();
    usersApiMock.getSettings.mockResolvedValue(null);
    usersApiMock.updateSettings.mockResolvedValue({
      notificationPreferences: {
        inApp: {
          tasks: false,
          projects: true,
          mentions: true,
          updates: true,
          system: true,
        },
        email: {
          tasks: true,
          projects: true,
          mentions: true,
        },
      },
    });

    const { NotificationsSettings } = await import(
      "@/app/settings/components/notifications-settings"
    );

    render(<NotificationsSettings />);

    await waitFor(() => expect(usersApiMock.getSettings).toHaveBeenCalledTimes(1));

    const toggles = screen.getAllByRole("checkbox");
    fireEvent.click(toggles[0]);

    await waitFor(() =>
      expect(usersApiMock.updateSettings).toHaveBeenCalledWith({
        notificationPreferences: {
          inApp: {
            tasks: false,
            projects: true,
            mentions: true,
            updates: true,
            system: true,
          },
          email: {
            tasks: true,
            projects: true,
            mentions: true,
          },
        },
      }),
      { timeout: 2000 },
    );
  });

  it("shows toast when autosave fails", async () => {
    vi.useRealTimers();
    usersApiMock.getSettings.mockResolvedValue(null);
    usersApiMock.updateSettings.mockRejectedValue(new Error("save failed"));

    const { NotificationsSettings } = await import(
      "@/app/settings/components/notifications-settings"
    );

    render(<NotificationsSettings />);

    await waitFor(() => expect(usersApiMock.getSettings).toHaveBeenCalledTimes(1));

    const toggles = screen.getAllByRole("checkbox");
    fireEvent.click(toggles[5]);

    await waitFor(() =>
      expect(toastErrorMock).toHaveBeenCalledWith("Failed to save notification preferences"),
      { timeout: 2000 },
    );
  });
});
