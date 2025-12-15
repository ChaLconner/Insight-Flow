/**
 * Card Component Tests
 * Tests for the Card UI component and its subcomponents
 */
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
  CardFooter,
} from "@/components/ui/card";

describe("Card Component", () => {
  it("renders Card component", () => {
    render(<Card data-testid="card">Card Content</Card>);
    expect(screen.getByTestId("card")).toBeInTheDocument();
    expect(screen.getByText("Card Content")).toBeInTheDocument();
  });

  it("applies custom className to Card", () => {
    render(
      <Card className="custom-class" data-testid="card">
        Content
      </Card>,
    );
    const card = screen.getByTestId("card");
    expect(card).toHaveClass("custom-class");
  });

  it("renders CardHeader component", () => {
    render(
      <Card>
        <CardHeader data-testid="card-header">Header Content</CardHeader>
      </Card>,
    );
    expect(screen.getByTestId("card-header")).toBeInTheDocument();
    expect(screen.getByText("Header Content")).toBeInTheDocument();
  });

  it("renders CardTitle with correct styling", () => {
    render(
      <Card>
        <CardHeader>
          <CardTitle>Test Title</CardTitle>
        </CardHeader>
      </Card>,
    );
    const title = screen.getByText("Test Title");
    expect(title).toBeInTheDocument();
    expect(title.tagName).toBe("H3");
  });

  it("renders CardDescription with muted styling", () => {
    render(
      <Card>
        <CardHeader>
          <CardDescription>Test Description</CardDescription>
        </CardHeader>
      </Card>,
    );
    const description = screen.getByText("Test Description");
    expect(description).toBeInTheDocument();
    expect(description.tagName).toBe("P");
  });

  it("renders CardContent component", () => {
    render(
      <Card>
        <CardContent data-testid="card-content">Main Content</CardContent>
      </Card>,
    );
    expect(screen.getByTestId("card-content")).toBeInTheDocument();
    expect(screen.getByText("Main Content")).toBeInTheDocument();
  });

  it("renders CardFooter component", () => {
    render(
      <Card>
        <CardFooter data-testid="card-footer">Footer Content</CardFooter>
      </Card>,
    );
    expect(screen.getByTestId("card-footer")).toBeInTheDocument();
    expect(screen.getByText("Footer Content")).toBeInTheDocument();
  });

  it("renders a complete Card with all subcomponents", () => {
    render(
      <Card data-testid="full-card">
        <CardHeader>
          <CardTitle>Full Card Title</CardTitle>
          <CardDescription>Full card description text</CardDescription>
        </CardHeader>
        <CardContent>
          <p>Card body content</p>
        </CardContent>
        <CardFooter>
          <button>Action Button</button>
        </CardFooter>
      </Card>,
    );

    expect(screen.getByTestId("full-card")).toBeInTheDocument();
    expect(screen.getByText("Full Card Title")).toBeInTheDocument();
    expect(screen.getByText("Full card description text")).toBeInTheDocument();
    expect(screen.getByText("Card body content")).toBeInTheDocument();
    expect(screen.getByText("Action Button")).toBeInTheDocument();
  });

  it("forwards ref correctly", () => {
    const ref = { current: null };
    render(
      <Card ref={ref} data-testid="ref-card">
        Content
      </Card>,
    );
    expect(ref.current).toBeInstanceOf(HTMLDivElement);
  });
});
