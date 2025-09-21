import { useRef, useCallback } from 'react';

export function useScreenReader() {
  const announcementRef = useRef<HTMLDivElement>(null);

  const announce = useCallback(
    (message: string, priority: 'polite' | 'assertive' = 'polite') => {
      if (announcementRef.current) {
        announcementRef.current.textContent = message;
        announcementRef.current.setAttribute('aria-live', priority);

        // Clear after announcement to allow repeated messages
        setTimeout(() => {
          if (announcementRef.current) {
            announcementRef.current.textContent = '';
          }
        }, 1000);
      }
    },
    []
  );

  return { announce, announcementRef };
}
