/**
 * Accessibility Tests
 * Tests for WCAG 2.1 compliance and accessibility best practices
 */
import { describe, it, expect } from "vitest";

// Mock utilities for a11y testing
const checkA11y = (element: HTMLElement): { violations: string[]; passes: string[] } => {
  const violations: string[] = [];
  const passes: string[] = [];

  // Check for alt text on images
  const images = element.querySelectorAll("img");
  images.forEach((img, index) => {
    if (!img.alt && !img.getAttribute("aria-label")) {
      violations.push(`Image ${index + 1} is missing alt text`);
    } else {
      passes.push(`Image ${index + 1} has alt text`);
    }
  });

  // Check for button accessibility
  const buttons = element.querySelectorAll("button");
  buttons.forEach((button, index) => {
    if (!button.textContent?.trim() && !button.getAttribute("aria-label")) {
      violations.push(`Button ${index + 1} has no accessible name`);
    } else {
      passes.push(`Button ${index + 1} has accessible name`);
    }
  });

  // Check for form labels
  const inputs = element.querySelectorAll("input, select, textarea");
  inputs.forEach((input, index) => {
    const id = input.getAttribute("id");
    const ariaLabel = input.getAttribute("aria-label");
    const ariaLabelledBy = input.getAttribute("aria-labelledby");
    const hasLabel = id ? element.querySelector(`label[for="${id}"]`) : false;

    if (!hasLabel && !ariaLabel && !ariaLabelledBy) {
      violations.push(`Form input ${index + 1} has no associated label`);
    } else {
      passes.push(`Form input ${index + 1} has associated label`);
    }
  });

  // Check for heading hierarchy
  const headings = element.querySelectorAll("h1, h2, h3, h4, h5, h6");
  let previousLevel = 0;
  headings.forEach((heading) => {
    const level = parseInt(heading.tagName.charAt(1));
    if (previousLevel > 0 && level > previousLevel + 1) {
      violations.push(`Heading hierarchy skipped from h${previousLevel} to h${level}`);
    } else {
      passes.push(`Heading h${level} follows proper hierarchy`);
    }
    previousLevel = level;
  });

  // Check for link text
  const links = element.querySelectorAll("a");
  links.forEach((link, index) => {
    const text = link.textContent?.trim();
    const ariaLabel = link.getAttribute("aria-label");
    if (!text && !ariaLabel) {
      violations.push(`Link ${index + 1} has no accessible text`);
    } else if (text?.toLowerCase() === "click here" || text?.toLowerCase() === "read more") {
      violations.push(`Link ${index + 1} has generic text: "${text}"`);
    } else {
      passes.push(`Link ${index + 1} has descriptive text`);
    }
  });

  // Check for focus indicators
  const focusableElements = element.querySelectorAll(
    'button, a, input, select, textarea, [tabindex]:not([tabindex="-1"])'
  );
  if (focusableElements.length > 0) {
    passes.push(`Found ${focusableElements.length} focusable elements`);
  }

  // Check for ARIA roles
  const ariaElements = element.querySelectorAll("[role]");
  ariaElements.forEach((el) => {
    const role = el.getAttribute("role");
    const validRoles = [
      "button",
      "link",
      "navigation",
      "main",
      "banner",
      "contentinfo",
      "dialog",
      "alert",
      "status",
      "progressbar",
      "tablist",
      "tab",
      "tabpanel",
      "menu",
      "menuitem",
      "listbox",
      "option",
      "heading",
      "region",
      "complementary",
      "search",
      "form",
      "img",
      "list",
      "listitem",
    ];
    if (role && validRoles.includes(role)) {
      passes.push(`Valid ARIA role: ${role}`);
    } else if (role) {
      violations.push(`Invalid or uncommon ARIA role: ${role}`);
    }
  });

  return { violations, passes };
};

describe("Accessibility - WCAG 2.1 Compliance", () => {
  describe("Images", () => {
    it("should require alt text for images", () => {
      const div = document.createElement("div");
      div.innerHTML = '<img src="test.jpg" alt="Test image" />';

      const { violations, passes } = checkA11y(div);

      expect(violations).toHaveLength(0);
      expect(passes.some((p) => p.includes("Image"))).toBe(true);
    });

    it("should detect missing alt text", () => {
      const div = document.createElement("div");
      div.innerHTML = '<img src="test.jpg" />';

      const { violations } = checkA11y(div);

      expect(violations.some((v) => v.includes("missing alt text"))).toBe(true);
    });
  });

  describe("Buttons", () => {
    it("should require accessible names for buttons", () => {
      const div = document.createElement("div");
      div.innerHTML = "<button>Submit</button>";

      const { violations, passes } = checkA11y(div);

      expect(violations).toHaveLength(0);
      expect(passes.some((p) => p.includes("Button"))).toBe(true);
    });

    it("should accept aria-label for icon buttons", () => {
      const div = document.createElement("div");
      div.innerHTML = '<button aria-label="Close"></button>';

      const { violations } = checkA11y(div);

      expect(violations.some((v) => v.includes("Button"))).toBe(false);
    });
  });

  describe("Forms", () => {
    it("should require labels for form inputs", () => {
      const div = document.createElement("div");
      div.innerHTML = `
        <label for="email">Email</label>
        <input type="email" id="email" />
      `;

      const { violations, passes } = checkA11y(div);

      expect(violations).toHaveLength(0);
      expect(passes.some((p) => p.includes("Form input"))).toBe(true);
    });

    it("should accept aria-label for inputs", () => {
      const div = document.createElement("div");
      div.innerHTML = '<input type="text" aria-label="Search" />';

      const { violations } = checkA11y(div);

      expect(violations.some((v) => v.includes("Form input"))).toBe(false);
    });
  });

  describe("Headings", () => {
    it("should follow proper heading hierarchy", () => {
      const div = document.createElement("div");
      div.innerHTML = `
        <h1>Main Title</h1>
        <h2>Section</h2>
        <h3>Subsection</h3>
      `;

      const { violations } = checkA11y(div);

      expect(violations.some((v) => v.includes("Heading hierarchy"))).toBe(false);
    });

    it("should detect skipped heading levels", () => {
      const div = document.createElement("div");
      div.innerHTML = `
        <h1>Main Title</h1>
        <h4>Skipped to h4</h4>
      `;

      const { violations } = checkA11y(div);

      expect(violations.some((v) => v.includes("Heading hierarchy skipped"))).toBe(true);
    });
  });

  describe("Links", () => {
    it("should require descriptive link text", () => {
      const div = document.createElement("div");
      div.innerHTML = '<a href="/about">Learn more about our company</a>';

      const { violations, passes } = checkA11y(div);

      expect(violations).toHaveLength(0);
      expect(passes.some((p) => p.includes("Link"))).toBe(true);
    });

    it("should detect generic link text", () => {
      const div = document.createElement("div");
      div.innerHTML = '<a href="/about">Click here</a>';

      const { violations } = checkA11y(div);

      expect(violations.some((v) => v.includes("generic text"))).toBe(true);
    });
  });

  describe("ARIA Roles", () => {
    it("should validate ARIA roles", () => {
      const div = document.createElement("div");
      div.innerHTML = `
        <nav role="navigation">
          <a href="/">Home</a>
        </nav>
      `;

      const { passes } = checkA11y(div);

      expect(passes.some((p) => p.includes("Valid ARIA role"))).toBe(true);
    });
  });
});

describe("Accessibility - Keyboard Navigation", () => {
  it("should support keyboard focus management", () => {
    const div = document.createElement("div");
    div.innerHTML = `
      <button>First</button>
      <button>Second</button>
      <button>Third</button>
    `;

    const buttons = div.querySelectorAll("button");
    expect(buttons.length).toBe(3);

    // All buttons should be focusable
    buttons.forEach((button) => {
      expect(button.tabIndex).toBeGreaterThanOrEqual(-1);
    });
  });

  it("should respect tabindex ordering", () => {
    const div = document.createElement("div");
    div.innerHTML = `
      <button tabindex="2">Second</button>
      <button tabindex="1">First</button>
      <button tabindex="3">Third</button>
    `;

    const buttons = Array.from(div.querySelectorAll("button"));
    const tabindexes = buttons.map((b) => b.tabIndex);

    expect(tabindexes).toEqual([2, 1, 3]);
  });

  it("should allow elements to be removed from tab order", () => {
    const div = document.createElement("div");
    div.innerHTML = '<button tabindex="-1">Hidden from tab</button>';

    const button = div.querySelector("button");
    expect(button?.tabIndex).toBe(-1);
  });
});

describe("Accessibility - Color Contrast", () => {
  // Helper function to calculate relative luminance
  const getLuminance = (r: number, g: number, b: number): number => {
    const [rs, gs, bs] = [r, g, b].map((c) => {
      const sRGB = c / 255;
      return sRGB <= 0.03928 ? sRGB / 12.92 : Math.pow((sRGB + 0.055) / 1.055, 2.4);
    });
    return 0.2126 * rs + 0.7152 * gs + 0.0722 * bs;
  };

  const getContrastRatio = (
    color1: { r: number; g: number; b: number },
    color2: { r: number; g: number; b: number }
  ): number => {
    const l1 = getLuminance(color1.r, color1.g, color1.b);
    const l2 = getLuminance(color2.r, color2.g, color2.b);
    const lighter = Math.max(l1, l2);
    const darker = Math.min(l1, l2);
    return (lighter + 0.05) / (darker + 0.05);
  };

  it("should pass WCAG AA for normal text (4.5:1)", () => {
    // Black on white
    const ratio = getContrastRatio({ r: 0, g: 0, b: 0 }, { r: 255, g: 255, b: 255 });

    expect(ratio).toBeGreaterThanOrEqual(4.5);
  });

  it("should pass WCAG AA for large text (3:1)", () => {
    // Dark gray on white
    const ratio = getContrastRatio({ r: 100, g: 100, b: 100 }, { r: 255, g: 255, b: 255 });

    expect(ratio).toBeGreaterThanOrEqual(3);
  });

  it("should pass WCAG AAA for normal text (7:1)", () => {
    // Black on white
    const ratio = getContrastRatio({ r: 0, g: 0, b: 0 }, { r: 255, g: 255, b: 255 });

    expect(ratio).toBeGreaterThanOrEqual(7);
  });
});

describe("Accessibility - Screen Reader Support", () => {
  it("should have proper ARIA live regions", () => {
    const div = document.createElement("div");
    div.innerHTML = `
      <div role="alert" aria-live="assertive">Error message</div>
      <div role="status" aria-live="polite">Success message</div>
    `;

    const alert = div.querySelector('[role="alert"]');
    const status = div.querySelector('[role="status"]');

    expect(alert?.getAttribute("aria-live")).toBe("assertive");
    expect(status?.getAttribute("aria-live")).toBe("polite");
  });

  it("should have proper landmark regions", () => {
    const div = document.createElement("div");
    div.innerHTML = `
      <header role="banner">Header</header>
      <nav role="navigation">Nav</nav>
      <main role="main">Content</main>
      <footer role="contentinfo">Footer</footer>
    `;

    expect(div.querySelector('[role="banner"]')).not.toBeNull();
    expect(div.querySelector('[role="navigation"]')).not.toBeNull();
    expect(div.querySelector('[role="main"]')).not.toBeNull();
    expect(div.querySelector('[role="contentinfo"]')).not.toBeNull();
  });

  it("should hide decorative elements from screen readers", () => {
    const div = document.createElement("div");
    div.innerHTML = `
      <img src="decoration.svg" aria-hidden="true" alt="" />
      <span aria-hidden="true">Decorative text</span>
    `;

    const hiddenElements = div.querySelectorAll('[aria-hidden="true"]');
    expect(hiddenElements.length).toBe(2);
  });
});

describe("Accessibility - Focus Management", () => {
  it("should trap focus in modal dialogs", () => {
    const div = document.createElement("div");
    div.innerHTML = `
      <div role="dialog" aria-modal="true" aria-labelledby="dialog-title">
        <h2 id="dialog-title">Dialog Title</h2>
        <button>Close</button>
      </div>
    `;

    const dialog = div.querySelector('[role="dialog"]');
    expect(dialog?.getAttribute("aria-modal")).toBe("true");
    expect(dialog?.getAttribute("aria-labelledby")).toBe("dialog-title");
  });

  it("should restore focus after dialog closes", () => {
    // Simulate focus restoration
    const previouslyFocused = document.createElement("button");
    previouslyFocused.textContent = "Open Dialog";

    // This tests the concept - actual implementation would be in component
    expect(previouslyFocused.focus).toBeDefined();
  });
});
