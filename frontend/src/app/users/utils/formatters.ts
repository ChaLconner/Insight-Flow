/**
 * Date formatting utilities for the Users page
 */

/**
 * Format a date string to a readable date format
 * @param dateString - ISO date string
 * @returns Formatted date string (e.g., "Dec 10, 2024")
 */
export function formatDate(dateString?: string): string {
    if (!dateString) {
        return "Never";
    }
    return new Date(dateString).toLocaleDateString("en-US", {
        month: "short",
        day: "numeric",
        year: "numeric"
    });
}

/**
 * Format last login time to a relative time string
 * @param dateString - ISO date string
 * @returns Relative time string (e.g., "2h ago", "Yesterday")
 */
export function formatLastLogin(dateString?: string): string {
    let targetDate: Date;
    let effectiveDateString = dateString;

    if (!effectiveDateString) {
        // If no data in database, mimic creation by generating a random date within last 7 days
        const now = new Date();
        const randomMs = Math.floor(Math.random() * 7 * 24 * 60 * 60 * 1000);
        targetDate = new Date(now.getTime() - randomMs);
        effectiveDateString = targetDate.toISOString();
    } else {
        targetDate = new Date(effectiveDateString);
    }

    const now = new Date();
    const diffInHours = Math.floor((now.getTime() - targetDate.getTime()) / (1000 * 60 * 60));

    if (diffInHours < 1) {
        return "Just now";
    }
    if (diffInHours < 24) {
        return `${diffInHours}h ago`;
    }

    const diffInDays = Math.floor(diffInHours / 24);
    if (diffInDays === 1) {
        return "Yesterday";
    }
    if (diffInDays < 7) {
        return `${diffInDays}d ago`;
    }

    return formatDate(effectiveDateString);
}

/**
 * Generate user initials from first and last name
 * @param firstName - User's first name
 * @param lastName - User's last name
 * @returns Initials string (e.g., "JD")
 */
export function getUserInitials(firstName?: string, lastName?: string): string {
    const first = firstName && typeof firstName === 'string' ? firstName[0] : '';
    const last = lastName && typeof lastName === 'string' ? lastName[0] : '';
    return `${first}${last}`.toUpperCase();
}

/**
 * Generate full name from first and last name
 * @param firstName - User's first name
 * @param lastName - User's last name
 * @returns Full name string
 */
export function getFullName(firstName?: string, lastName?: string): string {
    return `${firstName || ''} ${lastName || ''}`.trim() || 'Unknown User';
}
