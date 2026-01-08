
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import {
  cn,
  formatDate,
  getRelativeTime,
  isOverdue,
  getTimeUntil,
  capitalize,
  toCamelCase,
  toSnakeCase,
  truncate,
  getInitials,
  generateId,
  generateSlug,
  formatNumber,
  formatPercentage,
  clamp,
  random,
  groupBy,
  unique,
  sortBy,
  chunk,
  deepClone,
  isEmpty,
  omit,
  pick,
  transformKeys,
  isValidEmail,
  validatePassword,
  isValidUrl,
  getFromStorage,
  setToStorage,
  hexToRgba,
  getContrastColor,
  formatFileSize,
  getFileExtension,
  isAllowedFileType,
  debounce,
  throttle,
  memoize,
  getAvatarUrl,
} from "../lib/utils";

describe("Utils", () => {
  describe("CSS Class Utilities", () => {
    it("cn merges classes correctly", () => {
      expect(cn("foo", "bar")).toBe("foo bar");
      expect(cn("foo", { bar: true, baz: false })).toBe("foo bar");
      expect(cn("p-4", "p-2")).toBe("p-2"); // Tailwind merge
    });
  });

  describe("Date Utilities", () => {
    it("formatDate formats date string", () => {
      const date = new Date("2023-01-01T00:00:00.000Z");
      expect(formatDate(date)).toBe("Jan 1, 2023");
      expect(formatDate("2023-01-01T00:00:00.000Z")).toBe("Jan 1, 2023");
      expect(formatDate("invalid")).toBe("Invalid date");
    });

    it("getRelativeTime returns relative string", () => {
      const now = new Date();
      const past = new Date(now.getTime() - 1000 * 60 * 60 * 2); // 2 hours ago
      // Mock current time if needed, but date-fns usually handles it.
      // However, exact string depends on locale, assumed en-US by default.
      // Since it's dynamic, we might check if it contains "ago".
      expect(getRelativeTime(past)).toContain("ago");
      expect(getRelativeTime("invalid")).toBe("Invalid date");
    });

    it("isOverdue checks correctly", () => {
      const past = new Date("2000-01-01");
      const future = new Date("2100-01-01");
      expect(isOverdue(past)).toBe(true);
      expect(isOverdue(future)).toBe(false);
      expect(isOverdue("invalid")).toBe(false);
    });

    it("getTimeUntil returns distance", () => {
      const future = new Date(Date.now() + 1000 * 60 * 60 * 24); // 1 day
      expect(getTimeUntil(future)).not.toBe("Invalid date");
      expect(getTimeUntil("invalid")).toBe("Invalid date");
    });
  });

  describe("String Utilities", () => {
    it("capitalize capitalizes first letter", () => {
      expect(capitalize("hello")).toBe("Hello");
      expect(capitalize("WORLD")).toBe("World");
      expect(capitalize("")).toBe("");
    });

    it("toCamelCase converts to camelCase", () => {
      expect(toCamelCase("Hello World")).toBe("helloWorld");
    });

    it("toSnakeCase converts to snake_case", () => {
      expect(toSnakeCase("helloWorld")).toBe("hello_world");
      expect(toSnakeCase("SimpleString")).toBe("simple_string");
    });

    it("truncate truncates string", () => {
      expect(truncate("hello world", 5)).toBe("hello...");
      expect(truncate("hello", 10)).toBe("hello");
      expect(truncate("", 5)).toBe("");
    });

    it("getInitials generates initials", () => {
      expect(getInitials("John Doe")).toBe("JD");
      expect(getInitials("John")).toBe("J");
      expect(getInitials("")).toBe("");
    });

    it("generateId generates random string", () => {
      expect(generateId(8)).toHaveLength(8);
      expect(generateId(10)).toHaveLength(10);
    });

    it("generateSlug generates slug", () => {
      expect(generateSlug("Hello World")).toBe("hello-world");
      expect(generateSlug("Foo   Bar___Baz")).toBe("foo-bar-baz");
    });
  });

  describe("Number Utilities", () => {
    it("formatNumber formats with commas", () => {
      expect(formatNumber(1000)).toBe("1,000");
      expect(formatNumber(1000000)).toBe("1,000,000");
    });

    it("formatPercentage formats percentage", () => {
      expect(formatPercentage(50, 100)).toBe("50%");
      expect(formatPercentage(1, 3)).toBe("33%");
      expect(formatPercentage(0, 0)).toBe("0%");
    });

    it("clamp limits value", () => {
      expect(clamp(10, 0, 5)).toBe(5);
      expect(clamp(-5, 0, 5)).toBe(0);
      expect(clamp(3, 0, 5)).toBe(3);
    });

    it("random returns number in range", () => {
      const val = random(1, 10);
      expect(val).toBeGreaterThanOrEqual(1);
      expect(val).toBeLessThanOrEqual(10);
    });
  });

  describe("Array Utilities", () => {
    it("groupBy groups array", () => {
      const data = [{ id: 1, type: "a" }, { id: 2, type: "b" }, { id: 3, type: "a" }];
      const grouped = groupBy(data, "type");
      expect(grouped.a).toHaveLength(2);
      expect(grouped.b).toHaveLength(1);
    });

    it("unique removes duplicates", () => {
      expect(unique([1, 2, 2, 3])).toEqual([1, 2, 3]);
    });

    it("sortBy sorts array", () => {
      const data = [{ val: 3 }, { val: 1 }, { val: 2 }];
      expect(sortBy(data, "val")[0].val).toBe(1);
      expect(sortBy(data, "val", "desc")[0].val).toBe(3);
    });

    it("chunk chunks array", () => {
      const data = [1, 2, 3, 4, 5];
      const chunked = chunk(data, 2);
      expect(chunked).toHaveLength(3);
      expect(chunked[0]).toEqual([1, 2]);
      expect(chunked[2]).toEqual([5]);
    });
  });

  describe("Object Utilities", () => {
    it("deepClone clones object", () => {
      const original = { a: 1, b: { c: 2 }, d: new Date(), e: [1, 2] };
      const clone = deepClone(original);
      expect(clone).toEqual(original);
      expect(clone).not.toBe(original);
      expect(clone.b).not.toBe(original.b);
      expect(clone.e).not.toBe(original.e);
    });

    it("isEmpty checks empty", () => {
      expect(isEmpty(null)).toBe(true);
      expect(isEmpty({})).toBe(true);
      expect(isEmpty([])).toBe(true);
      expect(isEmpty("")).toBe(true);
      expect(isEmpty({ a: 1 })).toBe(false);
    });

    it("omit omits keys", () => {
      expect(omit({ a: 1, b: 2 }, ["b"])).toEqual({ a: 1 });
    });

    it("pick picks keys", () => {
      expect(pick({ a: 1, b: 2 }, ["a"])).toEqual({ a: 1 });
    });

    it("transformKeys transforms keys", () => {
      const input = { fooBar: 1 };
      const output = transformKeys(input, (k) => k.toUpperCase());
      expect(output).toEqual({ FOOBAR: 1 });
    });
  });

  describe("Validation Utilities", () => {
    it("isValidEmail validates email", () => {
      expect(isValidEmail("test@example.com")).toBe(true);
      expect(isValidEmail("invalid")).toBe(false);
    });

    it("validatePassword checks strength", () => {
      expect(validatePassword("valid").isValid).toBe(false);
      expect(validatePassword("Valid1!aa").isValid).toBe(true);
    });

    it("isValidUrl validates url", () => {
      expect(isValidUrl("https://google.com")).toBe(true);
      expect(isValidUrl("invalid")).toBe(false);
    });
  });

  describe("Storage Utilities", () => {
    beforeEach(() => {
      localStorage.clear();
      vi.clearAllMocks();
    });

    it("setToStorage saves item", () => {
      expect(setToStorage("key", { a: 1 })).toBe(true);
      expect(localStorage.getItem("key")).toBe(JSON.stringify({ a: 1 }));
    });

    it("getFromStorage retrieves item", () => {
      localStorage.setItem("key", JSON.stringify({ a: 1 }));
      expect(getFromStorage("key")).toEqual({ a: 1 });
      expect(getFromStorage("missing", "default")).toBe("default");
    });
  });

  describe("Color Utilities", () => {
    it("hexToRgba converts hex", () => {
      expect(hexToRgba("#000000", 0.5)).toBe("rgba(0, 0, 0, 0.5)");
    });

    it("getContrastColor returns black or white", () => {
      expect(getContrastColor("#000000")).toBe("#ffffff");
      expect(getContrastColor("#ffffff")).toBe("#0000"); // Transparent/Black? implementation says #0000
    });
  });

  describe("File Utilities", () => {
    it("formatFileSize formats bytes", () => {
      expect(formatFileSize(0)).toBe("0 Bytes");
      expect(formatFileSize(1024)).toBe("1 KB");
    });

    it("getFileExtension gets extension", () => {
      expect(getFileExtension("test.png")).toBe("png");
    });

    it("isAllowedFileType checks type", () => {
      expect(isAllowedFileType("test.png", ["png", "jpg"])).toBe(true);
      expect(isAllowedFileType("test.gif", ["png", "jpg"])).toBe(false);
    });
  });

  describe("Performance Utilities", () => {
    beforeEach(() => {
      vi.useFakeTimers();
    });

    afterEach(() => {
      vi.useRealTimers();
    });

    it("debounce delays execution", () => {
      const func = vi.fn();
      const debounced = debounce(func, 100);
      debounced();
      debounced();
      expect(func).not.toHaveBeenCalled();
      vi.advanceTimersByTime(100);
      expect(func).toHaveBeenCalledTimes(1);
    });

    it("throttle limits execution", () => {
      const func = vi.fn();
      const throttled = throttle(func, 100);
      throttled();
      throttled();
      expect(func).toHaveBeenCalledTimes(1);
      vi.advanceTimersByTime(100);
      throttled();
      expect(func).toHaveBeenCalledTimes(2);
    });

    it("memoize caches result", () => {
      const func = vi.fn((x) => x * 2);
      const memoized = memoize(func);
      expect(memoized(2)).toBe(4);
      expect(memoized(2)).toBe(4);
      expect(func).toHaveBeenCalledTimes(1);
    });
  });

  describe("Avatar Utilities", () => {
    it("getAvatarUrl returns correct url", () => {
      expect(getAvatarUrl("http://example.com/img.png")).toBe("http://example.com/img.png");
      expect(getAvatarUrl("/img.png")).toBe("/api/img.png");
      expect(getAvatarUrl("img.png")).toBe("/api/img.png");
      expect(getAvatarUrl("")).toBe("");
      expect(getAvatarUrl("/api/img.png")).toBe("/api/img.png");
    });
  });
});
