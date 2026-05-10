import React from "react";
import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

const searchUsersMock = vi.fn();

vi.mock("next/image", () => ({
  default: ({
    fill: _fill,
    ...props
  }: React.ImgHTMLAttributes<HTMLImageElement> & { fill?: boolean }) => (
    <img {...props} alt={props.alt ?? ""} />
  ),
}));

vi.mock("@/lib/api-endpoints", () => ({
  usersApi: {
    searchUsers: searchUsersMock,
  },
}));

vi.mock("@/hooks/use-click-outside", () => ({
  useClickOutside: vi.fn(),
}));

describe("UserSearchSelect", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.useRealTimers();
  });

  it("does not search until at least two characters are entered", async () => {
    const onChange = vi.fn();
    const { UserSearchSelect } = await import("@/components/ui/user-search-select");

    render(<UserSearchSelect value="" onChange={onChange} placeholder="Search users" />);

    fireEvent.change(screen.getByPlaceholderText("Search users"), {
      target: { value: "a" },
    });

    await act(async () => {
      await new Promise((resolve) => setTimeout(resolve, 350));
    });

    expect(searchUsersMock).not.toHaveBeenCalled();
    expect(onChange).toHaveBeenCalledWith("a");
    expect(screen.queryByText("No matching users found")).not.toBeInTheDocument();
  });

  it("searches and fills the input with the selected email when no custom selector is provided", async () => {
    searchUsersMock.mockResolvedValueOnce([
      {
        id: "user-1",
        email: "jane@example.com",
        username: "janedoe",
        firstName: "Jane",
        lastName: "Doe",
        avatar: "",
      },
    ]);

    const onChange = vi.fn();
    const { UserSearchSelect } = await import("@/components/ui/user-search-select");

    render(<UserSearchSelect value="" onChange={onChange} placeholder="Search users" />);

    fireEvent.change(screen.getByPlaceholderText("Search users"), {
      target: { value: "ja" },
    });

    await act(async () => {
      await new Promise((resolve) => setTimeout(resolve, 350));
    });

    expect(searchUsersMock).toHaveBeenCalledWith("ja");
    await waitFor(() => expect(screen.getByText("jane@example.com")).toBeInTheDocument());

    fireEvent.click(screen.getByRole("button", { name: /jane doe/i }));

    expect(onChange).toHaveBeenLastCalledWith("jane@example.com");
    expect(screen.getByDisplayValue("jane@example.com")).toBeInTheDocument();
  });

  it("calls onUserSelect and clears the query when a custom selector is provided", async () => {
    searchUsersMock.mockResolvedValueOnce([
      {
        id: "user-2",
        email: "sam@example.com",
        username: "sammie",
        firstName: "Sam",
        lastName: "Smith",
        avatar: "avatars/sam.png",
      },
    ]);

    const onChange = vi.fn();
    const onUserSelect = vi.fn();
    const { UserSearchSelect } = await import("@/components/ui/user-search-select");

    render(
      <UserSearchSelect
        value=""
        onChange={onChange}
        onUserSelect={onUserSelect}
        placeholder="Assign user"
      />,
    );

    fireEvent.change(screen.getByPlaceholderText("Assign user"), {
      target: { value: "sa" },
    });

    await act(async () => {
      await new Promise((resolve) => setTimeout(resolve, 350));
    });

    await waitFor(() => expect(screen.getByText("sam@example.com")).toBeInTheDocument());
    fireEvent.click(screen.getByRole("button", { name: /sam smith/i }));

    expect(onUserSelect).toHaveBeenCalledWith(
      expect.objectContaining({
        id: "user-2",
        email: "sam@example.com",
      }),
    );
    expect(onChange).toHaveBeenLastCalledWith("");
    expect(screen.getByPlaceholderText("Assign user")).toHaveValue("");
  });

  it("shows the empty state when the search request fails", async () => {
    const consoleErrorSpy = vi.spyOn(console, "error").mockImplementation(() => {});
    searchUsersMock.mockRejectedValueOnce(new Error("boom"));

    const { UserSearchSelect } = await import("@/components/ui/user-search-select");

    render(<UserSearchSelect value="" onChange={vi.fn()} placeholder="Search users" />);

    fireEvent.change(screen.getByPlaceholderText("Search users"), {
      target: { value: "zz" },
    });

    await act(async () => {
      await new Promise((resolve) => setTimeout(resolve, 350));
    });

    await waitFor(() => expect(screen.getByText("No matching users found")).toBeInTheDocument());
    expect(consoleErrorSpy).toHaveBeenCalledWith("Search failed:", expect.any(Error));

    consoleErrorSpy.mockRestore();
  });
});
