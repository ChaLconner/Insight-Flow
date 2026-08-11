// ===========================================
// useNotificationSound - Sound notification utilities
// ===========================================

import { useCallback } from "react";
import { NotificationPriority } from "@/types";

/**
 * Hook for playing notification sounds.
 * Supports different sounds based on notification type and priority.
 */
export const useNotificationSound = () => {
  const playNotificationSound = useCallback(
    (type: string, priority: string = NotificationPriority.MEDIUM) => {
      try {
        const AudioContextClass = window.AudioContext || (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext;
        const audioContext = new AudioContextClass();
        const oscillator = audioContext.createOscillator();
        const gainNode = audioContext.createGain();

        oscillator.connect(gainNode);
        gainNode.connect(audioContext.destination);

        // Configure sound based on type and priority
        const soundSettings: Record<string, { frequency: number; duration: number }> = {
          system: { frequency: 900, duration: 0.15 },
          task_assigned: { frequency: 1000, duration: 0.15 },
          comment: { frequency: 800, duration: 0.2 },
          default: { frequency: 800, duration: 0.15 },
        };
        const { frequency, duration } = soundSettings[type] ?? soundSettings.default;
        let volume = 0.1;

        // Adjust volume based on priority
        if (priority === "urgent") {
          volume *= 1.5;
        } else if (priority === "low") {
          volume *= 0.5;
        }

        // Reduce volume in quiet hours
        const currentHour = new Date().getHours();
        const isQuietHours = currentHour >= 22 || currentHour <= 7;

        if (isQuietHours) {
          volume *= 0.3;
        }

        oscillator.frequency.setValueAtTime(frequency, audioContext.currentTime);
        oscillator.type = "sine";

        gainNode.gain.setValueAtTime(volume, audioContext.currentTime);
        gainNode.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + duration);

        oscillator.start(audioContext.currentTime);
        oscillator.stop(audioContext.currentTime + duration);

        // Also try to play file if available
        try {
          const audio = new Audio("/sounds/notification.mp3");
          audio.volume = volume;
          audio.play().catch(() => {});
        } catch {
          /* Sound file not found, oscillator fallback was used */
        }
      } catch (error) {
        console.warn("Failed to play notification sound:", error);
      }
    },
    [],
  );

  return {
    playNotificationSound,
  };
};
