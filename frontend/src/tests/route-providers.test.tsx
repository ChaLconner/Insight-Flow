import { describe, expect, it } from "vitest";
import { isPublicLandingPath } from "@/components/providers/route-providers";

describe("route provider boundary", () => {
  it("keeps only the landing page on the lightweight provider path", () => {
    expect(isPublicLandingPath("/")).toBe(true);
    expect(isPublicLandingPath("/auth/login")).toBe(false);
    expect(isPublicLandingPath("/dashboard")).toBe(false);
    expect(isPublicLandingPath("/projects/123")).toBe(false);
  });
});
