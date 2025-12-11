import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

// ===========================================
// CSS Class Utilities
// ===========================================

/**
 * Utility function to merge CSS classes with proper handling of conflicting styles
 */
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

// ===========================================
// Date Utilities
// ===========================================

import { format, formatDistanceToNow, isValid, parseISO } from 'date-fns';

/**
 * Format date to a readable string
 */
export function formatDate(date: string | Date, formatStr: string = 'MMM d, yyyy'): string {
  const dateObj = typeof date === 'string' ? parseISO(date) : date;
  if (!isValid(dateObj)) {
    return 'Invalid date';
  }
  return format(dateObj, formatStr);
}

/**
 * Get relative time (e.g., "2 hours ago")
 */
export function getRelativeTime(date: string | Date): string {
  const dateObj = typeof date === 'string' ? parseISO(date) : date;
  if (!isValid(dateObj)) {
    return 'Invalid date';
  }
  return formatDistanceToNow(dateObj, { addSuffix: true });
}

/**
 * Check if date is overdue
 */
export function isOverdue(date: string | Date): boolean {
  const dateObj = typeof date === 'string' ? parseISO(date) : date;
  if (!isValid(dateObj)) {
    return false;
  }
  return new Date() > dateObj;
}

/**
 * Get time until a date
 */
export function getTimeUntil(date: string | Date): string {
  const dateObj = typeof date === 'string' ? parseISO(date) : date;
  if (!isValid(dateObj)) {
    return 'Invalid date';
  }
  return formatDistanceToNow(dateObj, { addSuffix: false });
}

// ===========================================
// String Utilities
// ===========================================

/**
 * Capitalize first letter of string
 */
export function capitalize(str: string): string {
  if (!str) {
    return '';
  }
  return str.charAt(0).toUpperCase() + str.slice(1).toLowerCase();
}

/**
 * Convert string to camelCase
 */
export function toCamelCase(str: string): string {
  return str
    .replace(/(?:^\w|[A-Z]|\b\w)/g, (word, index) => {
      return index === 0 ? word.toLowerCase() : word.toUpperCase();
    })
    .replace(/\s+/g, '');
}

/**
 * Convert string to snake_case
 */
export function toSnakeCase(str: string): string {
  return str
    .replace(/([A-Z])/g, '_$1')
    .toLowerCase()
    .replace(/^_/, '');
}

/**
 * Truncate string with ellipsis
 */
export function truncate(str: string, length: number = 50): string {
  if (!str) {
    return '';
  }
  if (str.length <= length) {
    return str;
  }
  return str.slice(0, length).trim() + '...';
}

/**
 * Generate initials from full name
 */
export function getInitials(name: string): string {
  if (!name) {
    return '';
  }
  return name
    .split(' ')
    .map(word => word.charAt(0).toUpperCase())
    .slice(0, 2)
    .join('');
}

/**
 * Generate random ID
 */
export function generateId(length: number = 8): string {
  const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789';
  let result = '';
  for (let i = 0; i < length; i++) {
    result += chars.charAt(Math.floor(Math.random() * chars.length));
  }
  return result;
}

/**
 * Generate slug from string
 */
export function generateSlug(str: string): string {
  return str
    .toLowerCase()
    .trim()
    .replace(/[^\w\s-]/g, '')
    .replace(/[\s_-]+/g, '-')
    .replace(/^-+|-+$/g, '');
}

// ===========================================
// Number Utilities
// ===========================================

/**
 * Format number with commas
 */
export function formatNumber(num: number): string {
  return new Intl.NumberFormat().format(num);
}

/**
 * Format percentage
 */
export function formatPercentage(value: number, total: number): string {
  if (total === 0) {
    return '0%';
  }
  const percentage = Math.round((value / total) * 100);
  return `${percentage}%`;
}

/**
 * Clamp number between min and max
 */
export function clamp(num: number, min: number, max: number): number {
  return Math.min(Math.max(num, min), max);
}

/**
 * Generate random number between min and max
 */
export function random(min: number, max: number): number {
  return Math.floor(Math.random() * (max - min + 1)) + min;
}

// ===========================================
// Array Utilities
// ===========================================

/**
 * Group array by key
 */
export function groupBy<T>(array: T[], key: keyof T): Record<string, T[]> {
  return array.reduce((groups, item) => {
    const groupKey = String(item[key]);
    if (!groups[groupKey]) {
      groups[groupKey] = [];
    }
    groups[groupKey].push(item);
    return groups;
  }, {} as Record<string, T[]>);
}

/**
 * Remove duplicates from array
 */
export function unique<T>(array: T[]): T[] {
  return Array.from(new Set(array));
}

/**
 * Sort array by key
 */
export function sortBy<T>(array: T[], key: keyof T, direction: 'asc' | 'desc' = 'asc'): T[] {
  return [...array].sort((a, b) => {
    const aVal = a[key];
    const bVal = b[key];

    if (aVal < bVal) { return direction === 'asc' ? -1 : 1; }
    if (aVal > bVal) { return direction === 'asc' ? 1 : -1; }
    return 0;
  });
}

/**
 * Chunk array into smaller arrays
 */
export function chunk<T>(array: T[], size: number): T[][] {
  const chunks: T[][] = [];
  for (let i = 0; i < array.length; i += size) {
    chunks.push(array.slice(i, i + size));
  }
  return chunks;
}

// ===========================================
// Object Utilities
// ===========================================

/**
 * Deep clone object
 */
export function deepClone<T>(obj: T): T {
  if (obj == null || typeof obj !== 'object') { return obj; }
  if (obj instanceof Date) { return new Date(obj.getTime()) as unknown as T; }
  if (obj instanceof Array) { return obj.map(item => deepClone(item)) as unknown as T; }
  if (typeof obj === 'object') {
    const copy = {} as T;
    Object.keys(obj).forEach(key => {
      copy[key as keyof T] = deepClone(obj[key as keyof T]);
    });
    return copy;
  }
  return obj;
}

/**
 * Check if object is empty
 */
export function isEmpty(obj: unknown): boolean {
  if (obj == null) { return true; }
  if (Array.isArray(obj) || typeof obj === 'string') { return obj.length === 0; }
  if (typeof obj === 'object') { return Object.keys(obj).length === 0; }
  return false;
}

/**
 * Omit properties from object
 */
export function omit<T, K extends keyof T>(obj: T, keys: K[]): Omit<T, K> {
  const result = { ...obj };
  keys.forEach(key => {
    delete result[key];
  });
  return result;
}

/**
 * Pick properties from object
 */
export function pick<T, K extends keyof T>(obj: T, keys: K[]): Pick<T, K> {
  const result = {} as Pick<T, K>;
  keys.forEach(key => {
    if (obj && typeof obj === 'object' && key in obj) {
      result[key] = obj[key];
    }
  });
  return result;
}

/**
 * Transform object keys
 */
export function transformKeys<T extends Record<string, unknown>>(
  obj: T,
  transformer: (key: string) => string
): Record<string, unknown> {
  const result: Record<string, unknown> = {};
  Object.keys(obj).forEach(key => {
    result[transformer(key)] = obj[key];
  });
  return result;
}

// ===========================================
// Validation Utilities
// ===========================================

/**
 * Validate email
 */
export function isValidEmail(email: string): boolean {
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  return emailRegex.test(email);
}

/**
 * Validate password strength
 */
export function validatePassword(password: string): { isValid: boolean; errors: string[] } {
  const errors: string[] = [];

  if (password.length < 8) {
    errors.push('Password must be at least 8 characters long');
  }

  if (!/[A-Z]/.test(password)) {
    errors.push('Password must contain at least one uppercase letter');
  }

  if (!/[a-z]/.test(password)) {
    errors.push('Password must contain at least one lowercase letter');
  }

  if (!/\d/.test(password)) {
    errors.push('Password must contain at least one number');
  }

  if (!/[!@#$%^&*()_+\-=\[\]{};':"\\|,.<>.?/]/.test(password)) { // eslint-disable-line no-useless-escape
    errors.push('Password must contain at least one special character');
  }

  return {
    isValid: errors.length === 0,
    errors,
  };
}

/**
 * Validate URL
 */
export function isValidUrl(url: string): boolean {
  try {
    new URL(url);
    return true;
  } catch {
    return false;
  }
}

// ===========================================
// Storage Utilities
// ===========================================

/**
 * Safe localStorage get
 */
export function getFromStorage<T>(key: string, defaultValue: T | null = null): T | null {
  if (typeof window === 'undefined') { return defaultValue; }

  try {
    const item = localStorage.getItem(key);
    return item ? JSON.parse(item) : defaultValue;
  } catch (error) {
    console.error(`Error reading from localStorage key "${key}":`, error);
    return defaultValue;
  }
}

/**
 * Safe localStorage set
 */
export function setToStorage(key: string, value: unknown): boolean {
  if (typeof window === 'undefined') { return false; }

  try {
    localStorage.setItem(key, JSON.stringify(value));
    return true;
  } catch (error) {
    console.error(`Error writing to localStorage key "${key}":`, error);
    return false;
  }
}

/**
 * Safe localStorage remove
 */
export function removeFromStorage(key: string): boolean {
  if (typeof window === 'undefined') { return false; }

  try {
    localStorage.removeItem(key);
    return true;
  } catch (error) {
    console.error(`Error removing localStorage key "${key}":`, error);
    return false;
  }
}

// ===========================================
// Color Utilities
// ===========================================

/**
 * Convert hex to rgba
 */
export function hexToRgba(hex: string, alpha: number = 1): string {
  const r = parseInt(hex.slice(1, 3), 16);
  const g = parseInt(hex.slice(3, 5), 16);
  const b = parseInt(hex.slice(5, 7), 16);
  return `rgba(${r}, ${g}, ${b}, ${alpha})`;
}

/**
 * Get contrast color (black or white) for given hex color
 */
export function getContrastColor(hex: string): string {
  const r = parseInt(hex.slice(1, 3), 16);
  const g = parseInt(hex.slice(3, 5), 16);
  const b = parseInt(hex.slice(5, 7), 16);
  const luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255;
  return luminance > 0.5 ? '#0000' : '#ffffff';
}

// ===========================================
// File Utilities
// ===========================================

/**
 * Format file size
 */
export function formatFileSize(bytes: number): string {
  if (bytes === 0) { return '0 Bytes'; }

  const k = 1024;
  const sizes = ['Bytes', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));

  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

/**
 * Get file extension
 */
export function getFileExtension(filename: string): string {
  return filename.slice((filename.lastIndexOf('.') - 1 >>> 0) + 2);
}

/**
 * Check if file type is allowed
 */
export function isAllowedFileType(filename: string, allowedTypes: string[]): boolean {
  const extension = getFileExtension(filename).toLowerCase();
  return allowedTypes.some(type => {
    if (type.startsWith('.')) {
      return extension === type.slice(1);
    }
    return extension === type;
  });
}

// ===========================================
// Performance Utilities
// ===========================================

/**
 * Debounce function
 */
export function debounce<T extends (...args: Parameters<T>) => void>(
  func: T,
  wait: number
): (...args: Parameters<T>) => void {
  let timeout: NodeJS.Timeout;
  return (...args: Parameters<T>) => {
    clearTimeout(timeout);
    timeout = setTimeout(() => func(...args), wait);
  };
}

/**
 * Throttle function
 */
export function throttle<T extends (...args: Parameters<T>) => void>(
  func: T,
  limit: number
): (...args: Parameters<T>) => void {
  let inThrottle: boolean;
  return (...args: Parameters<T>) => {
    if (!inThrottle) {
      func(...args);
      inThrottle = true;
      setTimeout(() => inThrottle = false, limit);
    }
  };
}

/**
 * Memoize function
 */
export function memoize<T extends (...args: Parameters<T>) => ReturnType<T>>(
  func: T
): (...args: Parameters<T>) => ReturnType<T> {
  const cache = new Map<string, ReturnType<T>>();
  return (...args: Parameters<T>): ReturnType<T> => {
    const key = JSON.stringify(args);
    if (cache.has(key)) {
      return cache.get(key) as ReturnType<T>;
    }
    const result = func(...args);
    cache.set(key, result);
    return result;
  };
}

// ===========================================
// Avatar/Profile Image Utilities
// ===========================================

/**
 * จัดการ URL ของรูปโปรไฟล์ให้สอดคล้องกันทั้งระบบ
 * @param avatarUrl URL ของรูปโปรไฟล์ (อาจเป็น relative path หรือ full URL)
 * @returns Full URL ที่พร้อมใช้งาน
 */
export function getAvatarUrl(avatarUrl?: string): string {
  if (!avatarUrl) { return ''; }

  // ถ้าเป็น full URL อยู่แล้ว ให้ใช้เลย
  if (avatarUrl.startsWith('http') || avatarUrl.startsWith('blob:')) {
    return avatarUrl;
  }

  // ถ้าเป็น relative path ให้ต่อกับ BASE_URL
  // Use inline constant to avoid require() - API_CONFIG.BASE_URL is '/api'
  const baseUrl = '/api';

  // ตรวจสอบว่า path ขึ้นต้นด้วย / หรือไม่
  const normalizedPath = avatarUrl.startsWith('/') ? avatarUrl : `/${avatarUrl}`;

  // Prevent double prefixing if path already starts with baseUrl
  if (normalizedPath.startsWith(baseUrl)) {
    return normalizedPath;
  }

  return `${baseUrl}${normalizedPath}`;
}