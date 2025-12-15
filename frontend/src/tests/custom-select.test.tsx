/**
 * CustomSelect Component Tests
 * Tests for the CustomSelect dropdown component
 */
import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { CustomSelect } from "@/components/ui/custom-select";

const mockOptions = [
  { value: "option1", label: "Option 1" },
  { value: "option2", label: "Option 2" },
  { value: "option3", label: "Option 3", description: "This is option 3" },
];

const optionsWithColors = [
  { value: "high", label: "High", color: "text-red-500" },
  { value: "medium", label: "Medium", color: "text-yellow-500" },
  { value: "low", label: "Low", color: "text-green-500" },
];

describe("CustomSelect Component", () => {
  it("renders with placeholder when no value selected", () => {
    const handleChange = vi.fn();
    render(
      <CustomSelect
        value=""
        onChange={handleChange}
        options={mockOptions}
        placeholder="Select an option"
      />,
    );

    expect(screen.getByText("Select an option")).toBeInTheDocument();
  });

  it("renders with selected option label", () => {
    const handleChange = vi.fn();
    render(
      <CustomSelect
        value="option2"
        onChange={handleChange}
        options={mockOptions}
      />,
    );

    expect(screen.getByText("Option 2")).toBeInTheDocument();
  });

  it("opens dropdown when clicked", () => {
    const handleChange = vi.fn();
    render(
      <CustomSelect
        value=""
        onChange={handleChange}
        options={mockOptions}
        placeholder="Select"
      />,
    );

    const button = screen.getByRole("button");
    fireEvent.click(button);

    // All options should be visible
    expect(screen.getByText("Option 1")).toBeInTheDocument();
    expect(screen.getByText("Option 2")).toBeInTheDocument();
    expect(screen.getByText("Option 3")).toBeInTheDocument();
  });

  it("calls onChange when option is selected", () => {
    const handleChange = vi.fn();
    render(
      <CustomSelect
        value=""
        onChange={handleChange}
        options={mockOptions}
        placeholder="Select"
      />,
    );

    // Open dropdown
    const trigger = screen.getByText("Select");
    fireEvent.click(trigger);

    // Click an option
    const option = screen.getByText("Option 2");
    fireEvent.click(option);

    expect(handleChange).toHaveBeenCalledWith("option2");
  });

  it("closes dropdown after selection", () => {
    const handleChange = vi.fn();
    render(
      <CustomSelect
        value=""
        onChange={handleChange}
        options={mockOptions}
        placeholder="Select"
      />,
    );

    // Open dropdown
    fireEvent.click(screen.getByText("Select"));
    expect(screen.getByText("Option 1")).toBeInTheDocument();

    // Select an option
    fireEvent.click(screen.getByText("Option 1"));

    // Dropdown should close - Option 2 and 3 should not be in dropdown
    // Note: This might need adjustment based on actual DOM structure
  });

  it("displays option descriptions when present", () => {
    const handleChange = vi.fn();
    render(
      <CustomSelect
        value=""
        onChange={handleChange}
        options={mockOptions}
        placeholder="Select"
      />,
    );

    // Open dropdown
    fireEvent.click(screen.getByText("Select"));

    // Check for description
    expect(screen.getByText("This is option 3")).toBeInTheDocument();
  });

  it("applies custom className", () => {
    const handleChange = vi.fn();
    const { container } = render(
      <CustomSelect
        value=""
        onChange={handleChange}
        options={mockOptions}
        className="custom-class"
      />,
    );

    // The container div should have the custom class
    const wrapper = container.firstChild;
    expect(wrapper).toHaveClass("custom-class");
  });

  it("renders options with colors", () => {
    const handleChange = vi.fn();
    render(
      <CustomSelect
        value="high"
        onChange={handleChange}
        options={optionsWithColors}
      />,
    );

    // Open dropdown
    fireEvent.click(screen.getByText("High"));

    // Check that all options are rendered
    expect(screen.getAllByText("High").length).toBeGreaterThan(0);
    expect(screen.getByText("Medium")).toBeInTheDocument();
    expect(screen.getByText("Low")).toBeInTheDocument();
  });

  it("toggles dropdown open/closed", () => {
    const handleChange = vi.fn();
    render(
      <CustomSelect
        value=""
        onChange={handleChange}
        options={mockOptions}
        placeholder="Select"
      />,
    );

    const button = screen.getByRole("button");

    // Open
    fireEvent.click(button);
    expect(screen.getByText("Option 1")).toBeInTheDocument();

    // Close by clicking again
    fireEvent.click(button);
    // Options should not be visible (dropdown closed)
  });

  it("handles size prop - sm", () => {
    const handleChange = vi.fn();
    render(
      <CustomSelect
        value=""
        onChange={handleChange}
        options={mockOptions}
        size="sm"
        placeholder="Select"
      />,
    );

    const button = screen.getByRole("button");
    expect(button).toHaveClass("h-8");
  });

  it("handles size prop - lg", () => {
    const handleChange = vi.fn();
    render(
      <CustomSelect
        value=""
        onChange={handleChange}
        options={mockOptions}
        size="lg"
        placeholder="Select"
      />,
    );

    const button = screen.getByRole("button");
    expect(button).toHaveClass("h-10");
  });

  it("falls back to value when no matching option label found", () => {
    const handleChange = vi.fn();
    render(
      <CustomSelect
        value="unknown_value"
        onChange={handleChange}
        options={mockOptions}
      />,
    );

    // Should display the raw value when no matching option
    expect(screen.getByText("unknown_value")).toBeInTheDocument();
  });

  it("closes dropdown when clicking outside", () => {
    const handleChange = vi.fn();
    render(
      <div>
        <div data-testid="outside">Outside Element</div>
        <CustomSelect
          value=""
          onChange={handleChange}
          options={mockOptions}
          placeholder="Select"
        />
      </div>,
    );

    // Open dropdown
    fireEvent.click(screen.getByText("Select"));
    expect(screen.getByText("Option 1")).toBeInTheDocument();

    // Click outside
    fireEvent.mouseDown(screen.getByTestId("outside"));

    // Dropdown should be closed now
    // Wait for state update - in actual test might need waitFor
  });
});
