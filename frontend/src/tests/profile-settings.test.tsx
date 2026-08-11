import React from "react";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

const updateUserProfileMock = vi.fn();
const updateUserAvatarMock = vi.fn();
const uploadAvatarMock = vi.fn();
const toastSuccessMock = vi.fn();
const toastErrorMock = vi.fn();

type ProfileTestUser = {
  id: string;
  firstName: string;
  lastName: string;
  email: string;
  username: string;
  phone: string;
  bio: string;
  avatar: string;
  name: string;
};

const createTestUser = (avatar = ""): ProfileTestUser => ({
    id: "user-1",
    firstName: "Jane",
    lastName: "Doe",
    email: "jane@example.com",
    username: "janedoe",
    phone: "+1234567890",
    bio: "Hello",
    avatar,
    name: "Jane Doe",
});

const authState: {
  user: ProfileTestUser | null;
  updateUserProfile: typeof updateUserProfileMock;
  updateUserAvatar: typeof updateUserAvatarMock;
} = {
  user: createTestUser(),
  updateUserProfile: updateUserProfileMock,
  updateUserAvatar: updateUserAvatarMock,
};

vi.mock("@/stores/auth-store", () => ({
  useAuthStore: (selector: (state: typeof authState) => unknown) => selector(authState),
}));

vi.mock("@/lib/api-endpoints", () => ({
  usersApi: {
    uploadAvatar: uploadAvatarMock,
  },
}));

vi.mock("@/app/settings/components/profile-settings.utils", () => ({
  canSubmitProfileForm: vi.fn(() => true),
}));

vi.mock("sonner", () => ({
  toast: {
    success: toastSuccessMock,
    error: toastErrorMock,
  },
}));

vi.mock("next/image", () => ({
  default: (props: React.ImgHTMLAttributes<HTMLImageElement>) => <img {...props} alt={props.alt ?? ""} />,
}));

describe("ProfileSettings", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    authState.user = createTestUser();
    updateUserProfileMock.mockResolvedValue(undefined);
    uploadAvatarMock.mockReset();
  });

  it("renders profile fields and saves edited data", async () => {
    const { ProfileSettings } = await import("@/app/settings/components/profile-settings");
    render(<ProfileSettings />);

    const firstName = await screen.findByDisplayValue("Jane");
    fireEvent.change(firstName, { target: { value: "Janet" } });
    fireEvent.click(screen.getByRole("button", { name: "Save Changes" }));

    await waitFor(() => expect(updateUserProfileMock).toHaveBeenCalled());
    expect(updateUserProfileMock).toHaveBeenCalledWith(
      expect.objectContaining({
        first_name: "Janet",
        last_name: "Doe",
        name: "Janet Doe",
      }),
    );
    expect(toastSuccessMock).toHaveBeenCalledWith("Profile saved successfully!");
  });

  it("shows validation errors for invalid email, phone, and bio", async () => {
    const { ProfileSettings } = await import("@/app/settings/components/profile-settings");
    render(<ProfileSettings />);

    fireEvent.change(await screen.findByDisplayValue("jane@example.com"), {
      target: { value: "invalid-email" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Save Changes" }));
    expect(toastErrorMock).toHaveBeenCalledWith("Please enter a valid email address");

    fireEvent.change(screen.getByLabelText("Email"), {
      target: { value: "jane@example.com" },
    });
    fireEvent.change(screen.getByLabelText("Bio"), {
      target: { value: "x".repeat(101) },
    });
    fireEvent.click(screen.getByRole("button", { name: "Save Changes" }));
    expect(toastErrorMock).toHaveBeenCalledWith("Bio is too long");

    fireEvent.change(screen.getByLabelText("Bio"), { target: { value: "Hello" } });
    fireEvent.change(screen.getByLabelText("Phone Number"), { target: { value: "bad" } });
    fireEvent.click(screen.getByRole("button", { name: "Save Changes" }));
    expect(toastErrorMock).toHaveBeenCalledWith("Please enter a valid phone number");

    fireEvent.change(screen.getByLabelText("Phone Number"), { target: { value: "-------" } });
    fireEvent.click(screen.getByRole("button", { name: "Save Changes" }));
    expect(toastErrorMock).toHaveBeenCalledWith("Please enter a valid phone number");
    expect(updateUserProfileMock).not.toHaveBeenCalled();
  });

  it("validates and uploads avatars, including upload failures", async () => {
    const createObjectURLMock = vi.spyOn(URL, "createObjectURL").mockReturnValue("blob:preview");
    const revokeObjectURLMock = vi.spyOn(URL, "revokeObjectURL").mockImplementation(() => undefined);
    const { ProfileSettings } = await import("@/app/settings/components/profile-settings");
    render(<ProfileSettings />);

    const fileInput = await screen.findByDisplayValue("Jane").then(() =>
      document.querySelector('input[type="file"]') as HTMLInputElement,
    );
    expect(fileInput).not.toBeNull();

    fireEvent.change(fileInput, { target: { files: [new File(["bad"], "bad.txt", { type: "text/plain" })] } });
    expect(toastErrorMock).toHaveBeenCalledWith("Invalid file type. Please upload PNG, JPG, or GIF.");

    fireEvent.change(fileInput, {
      target: { files: [new File(["large"], "large.png", { type: "image/png" })] },
    });
    Object.defineProperty(fileInput.files?.[0], "size", { value: 3 * 1024 * 1024 });
    fireEvent.change(fileInput, { target: { files: [fileInput.files?.[0]] } });
    expect(toastErrorMock).toHaveBeenCalledWith("File size too large. Maximum size is 2MB.");

    uploadAvatarMock.mockResolvedValueOnce({ avatar: "avatar.png" });
    fireEvent.change(fileInput, {
      target: { files: [new File(["ok"], "avatar.png", { type: "image/png" })] },
    });
    await waitFor(() => expect(toastSuccessMock).toHaveBeenCalledWith("Avatar updated successfully!"));
    expect(updateUserAvatarMock).toHaveBeenCalledWith("avatar.png");

    uploadAvatarMock.mockRejectedValueOnce(new Error("upload failed"));
    fireEvent.change(fileInput, {
      target: { files: [new File(["retry"], "retry.png", { type: "image/png" })] },
    });
    await waitFor(() => expect(toastErrorMock).toHaveBeenCalledWith(
      "Failed to upload avatar",
      expect.objectContaining({ description: "upload failed" }),
    ));
    expect(createObjectURLMock).toHaveBeenCalled();
    expect(revokeObjectURLMock).toHaveBeenCalled();
  });

  it("renders loading and existing-avatar states", async () => {
    const { ProfileSettings } = await import("@/app/settings/components/profile-settings");
    authState.user = null;
    const { rerender } = render(<ProfileSettings isLoading />);
    expect(document.querySelectorAll('[class*="animate-pulse"]').length).toBeGreaterThan(0);

    authState.user = createTestUser("avatar.png");
    rerender(<ProfileSettings />);
    expect(await screen.findByAltText("Profile")).toBeInTheDocument();
  });
});
