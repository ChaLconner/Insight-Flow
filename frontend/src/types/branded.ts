/**
 * Branded Types for Domain Safety - Staff/Principal Level TypeScript
 *
 * Provides compile-time safety for domain IDs and values.
 * Prevents mixing up different types of IDs (e.g., UserId vs ProjectId).
 */

// =============================================================================
// Brand Symbol
// =============================================================================

declare const brand: unique symbol;

/**
 * Creates a branded type from a base type.
 *
 * @example
 * type UserId = Brand<string, 'UserId'>;
 * const userId: UserId = 'abc123' as UserId; // Must explicitly cast
 */
export type Brand<T, B extends string> = T & { readonly [brand]: B };

// =============================================================================
// Domain ID Types
// =============================================================================

/** Branded UUID string for User IDs */
export type UserId = Brand<string, "UserId">;

/** Branded UUID string for Project IDs */
export type ProjectId = Brand<string, "ProjectId">;

/** Branded UUID string for Task IDs */
export type TaskId = Brand<string, "TaskId">;

/** Branded UUID string for Comment IDs */
export type CommentId = Brand<string, "CommentId">;

/** Branded UUID string for Notification IDs */
export type NotificationId = Brand<string, "NotificationId">;

/** Branded UUID string for File IDs */
export type FileId = Brand<string, "FileId">;

/** Branded string for email addresses */
export type Email = Brand<string, "Email">;

/** Branded string for JWT tokens */
export type JwtToken = Brand<string, "JwtToken">;

// =============================================================================
// ID Constructors with Validation
// =============================================================================

const UUID_REGEX =
  /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;
const EMAIL_REGEX = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

/**
 * User ID type guard and constructor
 */
export const UserId = {
  /**
   * Parse a string as a UserId (throws if invalid)
   */
  parse(id: string): UserId {
    if (!UserId.isValid(id)) {
      throw new Error(`Invalid UserId: ${id}`);
    }
    return id as UserId;
  },

  /**
   * Safely parse a string as a UserId (returns null if invalid)
   */
  safeParse(id: unknown): UserId | null {
    if (typeof id === "string" && UserId.isValid(id)) {
      return id as UserId;
    }
    return null;
  },

  /**
   * Check if a value is a valid UserId format
   */
  isValid(id: unknown): id is string {
    return typeof id === "string" && UUID_REGEX.test(id);
  },

  /**
   * Type guard to check if a value is a UserId
   */
  is(value: unknown): value is UserId {
    return UserId.isValid(value);
  },
};

/**
 * Project ID type guard and constructor
 */
export const ProjectId = {
  parse(id: string): ProjectId {
    if (!ProjectId.isValid(id)) {
      throw new Error(`Invalid ProjectId: ${id}`);
    }
    return id as ProjectId;
  },

  safeParse(id: unknown): ProjectId | null {
    if (typeof id === "string" && ProjectId.isValid(id)) {
      return id as ProjectId;
    }
    return null;
  },

  isValid(id: unknown): id is string {
    return typeof id === "string" && UUID_REGEX.test(id);
  },

  is(value: unknown): value is ProjectId {
    return ProjectId.isValid(value);
  },
};

/**
 * Task ID type guard and constructor
 */
export const TaskId = {
  parse(id: string): TaskId {
    if (!TaskId.isValid(id)) {
      throw new Error(`Invalid TaskId: ${id}`);
    }
    return id as TaskId;
  },

  safeParse(id: unknown): TaskId | null {
    if (typeof id === "string" && TaskId.isValid(id)) {
      return id as TaskId;
    }
    return null;
  },

  isValid(id: unknown): id is string {
    return typeof id === "string" && UUID_REGEX.test(id);
  },

  is(value: unknown): value is TaskId {
    return TaskId.isValid(value);
  },
};

/**
 * Email type guard and constructor
 */
export const Email = {
  parse(email: string): Email {
    if (!Email.isValid(email)) {
      throw new Error(`Invalid Email: ${email}`);
    }
    return email as Email;
  },

  safeParse(email: unknown): Email | null {
    if (typeof email === "string" && Email.isValid(email)) {
      return email as Email;
    }
    return null;
  },

  isValid(email: unknown): email is string {
    return typeof email === "string" && EMAIL_REGEX.test(email);
  },

  is(value: unknown): value is Email {
    return Email.isValid(value);
  },
};

// =============================================================================
// Exhaustive Type Checking
// =============================================================================

/**
 * Assert that a value is never (for exhaustive switch statements)
 *
 * @example
 * type Status = 'active' | 'inactive';
 * function handleStatus(status: Status) {
 *   switch (status) {
 *     case 'active': return 'A';
 *     case 'inactive': return 'I';
 *     default: return assertNever(status);
 *   }
 * }
 */
export function assertNever(x: never, message?: string): never {
  throw new Error(message ?? `Unexpected value: ${JSON.stringify(x)}`);
}

// =============================================================================
// Result Type (for explicit error handling)
// =============================================================================

/**
 * Result type for operations that can fail.
 * Forces explicit error handling without exceptions.
 */
export type Result<T, E = Error> =
  | { success: true; value: T }
  | { success: false; error: E };

export const Result = {
  ok<T>(value: T): Result<T, never> {
    return { success: true, value };
  },

  err<E>(error: E): Result<never, E> {
    return { success: false, error };
  },

  /**
   * Unwrap a result, throwing if it's an error
   */
  unwrap<T, E>(result: Result<T, E>): T {
    if (result.success) {
      return result.value;
    }
    throw result.error instanceof Error
      ? result.error
      : new Error(String(result.error));
  },

  /**
   * Unwrap a result with a default value
   */
  unwrapOr<T, E>(result: Result<T, E>, defaultValue: T): T {
    return result.success ? result.value : defaultValue;
  },

  /**
   * Map over a successful result
   */
  map<T, U, E>(result: Result<T, E>, fn: (value: T) => U): Result<U, E> {
    if (result.success) {
      return { success: true, value: fn(result.value) };
    }
    return result;
  },
};

// =============================================================================
// NonEmptyArray Type
// =============================================================================

/**
 * Array type that must have at least one element
 */
export type NonEmptyArray<T> = [T, ...T[]];

export const NonEmptyArray = {
  /**
   * Check if an array is non-empty
   */
  isNonEmpty<T>(arr: T[]): arr is NonEmptyArray<T> {
    return arr.length > 0;
  },

  /**
   * Safely get the first element (always defined for NonEmptyArray)
   */
  first<T>(arr: NonEmptyArray<T>): T {
    return arr[0];
  },

  /**
   * Create a NonEmptyArray from a value and optional rest
   */
  of<T>(first: T, ...rest: T[]): NonEmptyArray<T> {
    return [first, ...rest];
  },
};

// =============================================================================
// Opaque Types for Additional Safety
// =============================================================================

/**
 * Positive integer type
 */
export type PositiveInt = Brand<number, "PositiveInt">;

export const PositiveInt = {
  parse(n: number): PositiveInt {
    if (!Number.isInteger(n) || n <= 0) {
      throw new Error(`Invalid PositiveInt: ${n}`);
    }
    return n as PositiveInt;
  },

  isValid(n: unknown): n is number {
    return typeof n === "number" && Number.isInteger(n) && n > 0;
  },
};

/**
 * Percentage (0-100)
 */
export type Percentage = Brand<number, "Percentage">;

export const Percentage = {
  parse(n: number): Percentage {
    if (n < 0 || n > 100) {
      throw new Error(`Invalid Percentage: ${n}`);
    }
    return n as Percentage;
  },

  isValid(n: unknown): n is number {
    return typeof n === "number" && n >= 0 && n <= 100;
  },
};

// =============================================================================
// Type Utilities
// =============================================================================

/**
 * Make specified properties required
 */
export type WithRequired<T, K extends keyof T> = T & Required<Pick<T, K>>;

/**
 * Make all properties in T optional except for those in K
 */
export type PartialExcept<T, K extends keyof T> = Partial<Omit<T, K>> &
  Pick<T, K>;

/**
 * Extract the element type from an array type
 */
export type ArrayElement<T> = T extends (infer E)[] ? E : never;

/**
 * Make all properties deeply readonly
 */
export type DeepReadonly<T> = {
  readonly [P in keyof T]: T[P] extends object ? DeepReadonly<T[P]> : T[P];
};

/**
 * Make all properties deeply partial
 */
export type DeepPartial<T> = {
  [P in keyof T]?: T[P] extends object ? DeepPartial<T[P]> : T[P];
};
