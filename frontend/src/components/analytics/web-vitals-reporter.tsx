"use client";

/**
 * Web Vitals Reporter
 * Tracks Core Web Vitals metrics for performance monitoring.
 * 
 * Metrics tracked:
 * - LCP (Largest Contentful Paint): Loading performance
 * - FID (First Input Delay): Interactivity
 * - CLS (Cumulative Layout Shift): Visual stability
 * - FCP (First Contentful Paint): Perceived load speed
 * - TTFB (Time to First Byte): Server response time
 */

import { useEffect } from "react";

interface WebVitalMetric {
  id: string;
  name: string;
  value: number;
  rating: "good" | "needs-improvement" | "poor";
  delta: number;
  navigationType: string;
}

// Thresholds for Web Vitals (based on Google's recommendations)
const THRESHOLDS = {
  LCP: { good: 2500, poor: 4000 },
  FID: { good: 100, poor: 300 },
  CLS: { good: 0.1, poor: 0.25 },
  FCP: { good: 1800, poor: 3000 },
  TTFB: { good: 800, poor: 1800 },
  INP: { good: 200, poor: 500 },
} as const;

function getRating(
  name: string,
  value: number
): "good" | "needs-improvement" | "poor" {
  const threshold = THRESHOLDS[name as keyof typeof THRESHOLDS];
  if (!threshold) {
    return "good";
  }

  if (value <= threshold.good) {
    return "good";
  }
  if (value <= threshold.poor) {
    return "needs-improvement";
  }
  return "poor";
}

// Custom analytics endpoint (optional)
const ANALYTICS_ENDPOINT = process.env.NEXT_PUBLIC_ANALYTICS_ENDPOINT;

async function sendToAnalytics(metric: WebVitalMetric) {
  // Log to console in development
  if (process.env.NODE_ENV === "development") {
    const color =
      metric.rating === "good"
        ? "\x1b[32m" // green
        : metric.rating === "needs-improvement"
          ? "\x1b[33m" // yellow
          : "\x1b[31m"; // red
    const reset = "\x1b[0m";

    console.log(
      `${color}[Web Vital]${reset} ${metric.name}: ${metric.value.toFixed(2)}ms (${metric.rating})`
    );
  }

  // Send to analytics endpoint if configured
  if (ANALYTICS_ENDPOINT) {
    try {
      const body = JSON.stringify({
        ...metric,
        timestamp: Date.now(),
        url: window.location.href,
        userAgent: navigator.userAgent,
      });

      // Use sendBeacon for reliable delivery
      if (navigator.sendBeacon) {
        navigator.sendBeacon(ANALYTICS_ENDPOINT, body);
      } else {
        // Fallback to fetch
        fetch(ANALYTICS_ENDPOINT, {
          method: "POST",
          body,
          headers: { "Content-Type": "application/json" },
          keepalive: true,
        });
      }
    } catch (error) {
      // Silently fail - don't break the app for analytics
      console.warn("Failed to send web vital metric:", error);
    }
  }
}

function onPerfEntry(metric: {
  name: string;
  value: number;
  id: string;
  delta: number;
  navigationType: string;
}) {
  const webVitalMetric: WebVitalMetric = {
    id: metric.id,
    name: metric.name,
    value: metric.value,
    rating: getRating(metric.name, metric.value),
    delta: metric.delta,
    navigationType: metric.navigationType,
  };

  sendToAnalytics(webVitalMetric);
}

/**
 * Hook to initialize Web Vitals reporting.
 * Should be used in the root layout or app component.
 */
export function useWebVitals() {
  useEffect(() => {
    // Dynamically import web-vitals to avoid SSR issues
    import("web-vitals").then(({ onCLS, onFCP, onLCP, onTTFB, onINP }) => {
      onCLS(onPerfEntry);
      onFCP(onPerfEntry);
      onLCP(onPerfEntry);
      onTTFB(onPerfEntry);
      onINP(onPerfEntry);
    }).catch(() => {
      // web-vitals not installed, that's okay
      console.debug("web-vitals library not available");
    });
  }, []);
}

/**
 * Component to initialize Web Vitals reporting.
 * Alternative to the hook for class components or simpler usage.
 */
export function WebVitalsReporter() {
  useWebVitals();
  return null;
}

export default WebVitalsReporter;
